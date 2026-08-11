"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Flattened agent tools: exposes calendar, weather, search, and web
utility functions and tool wrappers used by the JADE assistant.
"""

# ------- Import Section -------
import os
import datetime
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from strands import Agent, tool
from strands.models.ollama import OllamaModel
import requests
import time
from dotenv import load_dotenv
from newsapi import NewsApiClient
import wikipedia
import yfinance as yf
from duckduckgo_search import DDGS
from datetime import date
import json
from pathlib import Path

# ------- Constants and Initialization Section -------
load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/calendar']
URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight showers",
    81: "Moderate showers",
    82: "Violent showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
API = NewsApiClient(NEWS_API_KEY) if NEWS_API_KEY else None

wikipedia.set_user_agent("JADE/1.0 (justin_m_baratta@gmail.com)")
BASE_DIR = Path.cwd()

def init_google_calendar():
    """Initialize Google Calendar API client using local credentials/token files.

    Returns a service object from `googleapiclient.discovery.build`.
    """

    # Attempt to load saved credentials from `token.json` first.
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
                token.write(creds.to_json())
    service = build("calendar", "v3", credentials=creds)
    return service

SERVICE = init_google_calendar()

# ------- Helper Functions Section -------
def get_now_iso() -> str:
    # Current time in LA timezone as ISO string (useful for Google Calendar queries)
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()

def get_geocode(city: str = "Reno") -> tuple:
    # Query the open-meteo geocoding endpoint for a single match
    params = {'name': city, 'count': 1}
    response = requests.get(GEOCODING_URL, params=params, timeout=10)

    if not response.ok:
        raise Exception(f"Geocoding failed: {response.status_code}")

    results = response.json().get("results", [])
    if not results:
        raise Exception(f"No geocoding result found for {city}")

    result = results[0]
    return result["latitude"], result["longitude"]

def ddg_search(query: str = "") -> str:
    try:
        # Use DuckDuckGo search wrapper to fetch short text results
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return f"No results found for: '{query}'"
        return "\n".join(f"Title: {r['title']}\nSnippet: {r['body']}\n" for r in results)
    except Exception as e:
        return f"Search error: {e}"

def wiki_lookup(topic: str = "") -> str:
    try:
        # Attempt to fetch a concise Wikipedia summary for the topic
        summary = wikipedia.summary(topic, auto_suggest=True)
        return f"Wikipedia Summary for '{topic}': {summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Topic ambiguous. Try one of these: {e.options[:3]}"
    except Exception as e:
        return f"Wikipedia error: {e}"

def fetch_stock(ticker: str = "") -> dict:
    try:
        # Query yfinance for the ticker metadata and current price
        info = yf.Ticker(ticker).info
        return {
            "symbol": ticker.upper(),
            "price": info.get("currentPrice"),
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
            "company": info.get("longName"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch {ticker}: {e}"}

def entry_path(type_entry: str = "", file_title: str = "") -> Path:
    # Construct a filesystem path for a named JSON entry (notes, todos, etc.)
    return BASE_DIR / type_entry / f"{file_title}.json"

def write_json(path: Path, payload: dict = {}) -> None:
    # Ensure the target directory exists, then write JSON with indentation
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

# ------- Tools Section -------

#! Google Calendar Tools
@tool
def read_upcoming_events(max_results: int = 5) -> str:
    """
    Retrieves upcoming calendar events

    Args:
        max_results: int, maximum number of events to return
    """

    # Collect a small list of upcoming events for display
    upcoming_events = []
    now = get_now_iso()

    try:
        # Call Google Calendar API for upcoming events
        events_result = SERVICE.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return f"No upcoming events found."

        # Normalize event start field and collect id/summary for each entry
        for event in events:
            start = event['start'].get("dateTime", event['start'].get("date"))
            data = {
                'ID': event['id'],
                "Start": start,
                "Event": event.get("summary")
            }
            upcoming_events.append(data)
        return f"Next {max_results} Events: {upcoming_events}"
    except Exception as e:
        return f"An error occurred when trying to get upcoming events: {e}"

# @tool
# def add_event(summary: str, start_time: str, end_time: str) -> str:
#     """
#     Creates a new Google Calendar event.
    
#     CRITICAL: Always look up the current date/time first using `get_now` or `get_now_iso`
#     to calculate relative days like 'today' or 'tomorrow'.

#     Args:
#         summary: Short concise title of the event (e.g., 'Basketball Practice').
#         start_time: Full ISO date-time format 'YYYY-MM-DDTHH:MM:SS' in 24-hour time 
#                     (e.g., '2026-07-25T16:30:00' for 4:30 PM). 
#                     For all-day events, use 'YYYY-MM-DD'.
#         end_time: Full ISO date-time format 'YYYY-MM-DDTHH:MM:SS' in 24-hour time 
#                   (e.g., '2026-07-25T17:30:00' for 5:30 PM). 
#                   For all-day events, use 'YYYY-MM-DD'.
#     """
#     print(start_time, end_time)
#     is_all_day = len(start_time) <= 10

#     if is_all_day:
#         event = {
#             "summary": summary,
#             "description": "",
#             "start": {"date": start_time},
#             "end": {"date": end_time}
#         }
#     else:
#         tz = ZoneInfo("America/Los_Angeles")
        
#         clean_start = start_time.rstrip('Z')
#         clean_end = end_time.rstrip('Z')

#         dt_start = datetime.datetime.fromisoformat(clean_start).replace(tzinfo=tz)
#         dt_end = datetime.datetime.fromisoformat(clean_end).replace(tzinfo=tz)

#         event = {
#             "summary": summary,
#             "description": "",
#             "start": {
#                 'dateTime': dt_start.isoformat(),
#                 'timeZone': 'America/Los_Angeles'
#             },
#             'end': {
#                 'dateTime': dt_end.isoformat(),
#                 'timeZone': 'America/Los_Angeles'
#             }
#         }

#     try:
#         created_event = SERVICE.events().insert(calendarId='primary', body=event).execute()
#         return f"Success! Event created: {created_event.get('htmlLink')} (ID: {created_event.get('id')})"
#     except Exception as e:
#         return f"Error adding event: {e}"
@tool
def add_event(summary: str, start_time: str, end_time: str) -> str:
    """
    Creates a new Google Calendar event.
    
    CRITICAL: Always look up the current date/time first using `get_now` or `get_now_iso`
    to calculate relative days like 'today' or 'tomorrow'.

    Args:
        summary: Short concise title of the event (e.g., 'Basketball Practice').
        start_time: Full ISO date-time format 'YYYY-MM-DDTHH:MM:SS' in 24-hour time 
                    (e.g., '2026-08-11T16:30:00-07:00' for 4:30 PM). 
                    For all-day events, use 'YYYY-MM-DD'.
        end_time: Full ISO date-time format 'YYYY-MM-DDTHH:MM:SS' in 24-hour time 
                  (e.g., '2026-08-11T17:30:00-07:00' for 5:30 PM). 
                  For all-day events, use 'YYYY-MM-DD'.
    """
    is_all_day = len(start_time) <= 10

    if is_all_day:
        event = {
            "summary": summary,
            "description": "",
            "start": {"date": start_time},
            "end": {"date": end_time}
        }
    else:
        event = {
            "summary": summary,
            "description": "",
            "start": {
                'dateTime': start_time,
                'timeZone': 'America/Los_Angeles'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Los_Angeles'
            }
        }

    try:
        created_event = SERVICE.events().insert(calendarId='primary', body=event).execute()
        return f"Success! Event created: {created_event.get('htmlLink')} (ID: {created_event.get('id')})"
    except Exception as e:
        return f"Error adding event: {e}"
    
@tool
def delete_event(event_id: str) -> str:
    """
    Deletes an event by its ID. Look up event IDs using `get_events_and_ids` first.

    Args:
        event_id: Unique string ID of the event to delete.
    """
    try:
        SERVICE.events().delete(calendarId='primary', eventId=event_id).execute()
        return f"Success! Event ID {event_id} deleted."
    except Exception as e:
        return f"Error deleting event: {e}"

@tool
def get_now() -> str:
    """
    Useful helper tool (yes, a duplicate) to get the current
    ISO date and time for America/Los_Angeles
    """
    return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()

@tool
def get_events_and_ids() -> str:
    """
    Returns a mapping of upcoming event names to their IDs and start times.
    Use this to find an event ID before deleting or editing an entry.
    """
    data = {}
    now = get_now_iso()

    try:
        events_result = SERVICE.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            return f"No events found: {events}"

        for event in events:
            data[f"{event.get('summary')}"] = (
                event['id'], 
                event['start'].get('dateTime', event['start'].get('date'))
            )
        return f"Data: {data}"
    except Exception as e:
        return f"Error fetching event IDs: {e}"

def list_calendar_tools() -> list:
    return [
        read_upcoming_events,
        delete_event,
        add_event,
        get_events_and_ids
    ]

#! Weather Tools
@tool
def get_current_weather(city: str = "Reno") -> dict:
    """Get the current weather in a city."""
    latitude, longitude = get_geocode(city=city)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "wind_speed_10m", "precipitation", "weather_code"],
        "temperature_unit": "fahrenheit",
    }

    response = requests.get(URL, params=params, timeout=10)
    if not response.ok:
        raise Exception(f"Failed to fetch weather data: {response.status_code}")

    weather_current = response.json()["current"]
    weather_current["weather_code"] = WMO_CODES[int(weather_current["weather_code"])]
    weather_current["city"] = city
    return weather_current

@tool
def get_forecast(city: str = "Reno", days: int = 7):
    """Get the forecast for a certain number of days in a city."""
    latitude, longitude = get_geocode(city=city)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "weather_code"],
        "temperature_unit": "fahrenheit",
        "forecast_days": days,
    }

    response = requests.get(URL, params=params, timeout=10)
    if not response.ok:
        raise Exception(f"Failed to fetch forecast data: {response.status_code}")

    results = response.json()["daily"]
    results["city"] = city
    results["weather_code"] = [WMO_CODES[int(code)] for code in results.get("weather_code", [])]
    return results

@tool
def get_weather_summary(city: str = "Reno", days: int = 3) -> str:
    """Return a compact current + forecast snapshot for a city."""
    current = get_current_weather(city)
    forecast = get_forecast(city=city, days=days)
    summary = {
        "city": city,
        "current": current,
        "forecast": {
            "dates": forecast.get("time", []),
            "highs": forecast.get("temperature_2m_max", []),
            "lows": forecast.get("temperature_2m_min", []),
            "precipitation": forecast.get("precipitation_sum", []),
            "conditions": forecast.get("weather_code", []),
        },
    }
    return f"Weather summary in {city} for next {days} days: {summary}"

@tool
def get_forecast_summary(city: str = "Reno", days: int = 3) -> str:
    """Return a human-readable forecast summary for the next few days."""
    forecast = get_forecast(city=city, days=days)
    lines = [f"Forecast for {city}:"]
    for day, high, low, precipitation, condition in zip(
        forecast.get("time", []),
        forecast.get("temperature_2m_max", []),
        forecast.get("temperature_2m_min", []),
        forecast.get("precipitation_sum", []),
        forecast.get("weather_code", []),
    ):
        lines.append(f"- {day}: high {high}°F, low {low}°F, precipitation {precipitation}, {condition}")
    return "\n".join(lines)

def list_weather_tools() -> list:
    return [
        get_current_weather,
        get_forecast,
        get_weather_summary,
        get_forecast_summary
    ]

#! Web Tools
@tool
def search_and_lookup(query: str) -> str:
    """Search the live web or Wikipedia for general knowledge, current events, and facts."""
    wiki_res = wiki_lookup(query)
    if "error" in wiki_res.lower() or "ambiguous" in wiki_res.lower():
        return ddg_search(query)
    return wiki_res

@tool
def get_stock_prices(tickers: list) -> dict:
    """Get the current stock price details for a list of ticker symbols (e.g. ['AAPL', 'TSLA'])."""
    prices = {}
    for ticker in tickers:
        time.sleep(0.5)  # Quick rate-limit cushion
        prices[ticker] = fetch_stock(ticker)
    return prices

@tool
def get_news_headlines() -> list:
    """Get the top news headlines."""
    if not API:
        return [{"title": "News API key missing", "description": "Configure NEWS_API_KEY."}]
    try:
        return API.get_top_headlines().get("articles", [])[:5]
    except Exception as e:
        return [{"title": "News API Error", "description": str(e)}]

def list_web_tools() -> list:
    return [
        search_and_lookup,
        get_stock_prices,
        get_news_headlines
    ]

#! Writing Tools
@tool
def create_notes_entry(content: str) -> None:
    """Create a new notes entry."""
    today = date.today().strftime("%Y-%m-%d")
    file_name = f"{today}_Notes"
    payload = {"date": today, "content": content}
    write_json(entry_path("notes", file_name), payload)

@tool
def create_todo_entry(tasks: list, tags: list | None = None) -> None:
    """Create a new todo entry."""
    tags = tags or []
    today = date.today().strftime("%Y-%m-%d")
    file_name = f"{today}_Todos"
    payload = {
        "date": today,
        "todos": [
            {"task": task, "completed": False, "tag": tags[i] if i < len(tags) else ""}
            for i, task in enumerate(tasks)
        ],
    }
    write_json(entry_path("todos", file_name), payload)

@tool
def create_journal_entry(content: str) -> None:
    """Create a new journal entry."""
    today = date.today().strftime("%Y-%m-%d")
    file_name = f"{today}_Journals"
    payload = {"date": today, "content": content}
    write_json(entry_path("journals", file_name), payload)

@tool
def list_writing_entries(query: str = "", type_entry: str = "notes") -> dict:
    """Return a list of writing entries based on the query and type."""
    if type_entry not in ["notes", "todos", "journals"]:
        return {}

    folder = BASE_DIR / type_entry
    results = {}
    for file in sorted(folder.glob("*.json")):
        if query.lower() in file.name.lower() or not query:
            with file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if type_entry == "todos":
                preview = [todo.get("task", "") for todo in data.get("todos", [])]
            else:
                preview = data.get("content", "")[:75]

            results[file.stem] = preview

    return results

@tool
def search_entries(query: str = "", type_entry: str = "notes") -> dict:
    """Search writing entries by title or content using a simple substring match."""
    return list_writing_entries(query=query, type_entry=type_entry)

@tool
def read_entry(file_title: str) -> dict:
    """Read a writing entry by its title."""
    for type_entry in ["notes", "todos", "journals"]:
        path = entry_path(type_entry, file_title)
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)

    return {}

@tool
def complete_todo(file_title: str, task: str) -> str:
    """Mark a todo as complete."""
    path = entry_path("todos", file_title)
    if not path.exists():
        return f"Todo '{file_title}' not found"

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    todo_match = next((todo for todo in data.get("todos", []) if todo.get("task", "").lower() == task.lower()), None)
    if not todo_match:
        return f"Task '{task}' not found in '{file_title}'"

    todo_match["completed"] = True
    write_json(path, data)
    return f"Task '{task}' marked as complete"

@tool
def get_incomplete_todos() -> dict:
    """Return a list of all incomplete todos."""
    results = {}
    for file in sorted((BASE_DIR / "todos").glob("*.json")):
        with file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        incomplete = [todo for todo in data.get("todos", []) if not todo.get("completed", False)]
        if incomplete:
            results[file.stem] = incomplete

    return results

@tool
def get_todo_summary() -> dict:
    """Return a simple summary of todo progress across files."""
    totals = {"files": 0, "tasks": 0, "completed": 0, "incomplete": 0, "by_tag": {}}
    for file in sorted((BASE_DIR / "todos").glob("*.json")):
        with file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        totals["files"] += 1
        for todo in data.get("todos", []):
            totals["tasks"] += 1
            if todo.get("completed", False):
                totals["completed"] += 1
            else:
                totals["incomplete"] += 1
            tag = todo.get("tag", "") or "untagged"
            totals["by_tag"][tag] = totals["by_tag"].get(tag, 0) + 1
    return totals

@tool
def add_task(file_title: str, task: str, tag: str = "") -> str:
    """Add a new task to a todo entry."""
    path = entry_path("todos", file_title)
    if not path.exists():
        return f"Todo '{file_title}' not found"

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    data["todos"].append({"task": task, "completed": False, "tag": tag})
    write_json(path, data)
    return f"Task '{task}' added to '{file_title}'"

@tool
def update_entry(file_title: str, content: str, mode: str = "w") -> str:
    """Update a writing entry by its title."""
    for type_entry in ["notes", "journals"]:
        path = entry_path(type_entry, file_title)
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if mode == "a":
            data["content"] = f"{data.get('content', '')}\n{content}".strip()
        else:
            data["content"] = content

        write_json(path, data)
        return f"Entry '{file_title}' updated"

    return f"Entry '{file_title}' not found"

@tool
def get_today() -> str:
    return date.today().strftime("%Y-%m-%d")

def list_writing_tools() -> list:
    return [
        create_notes_entry,
        create_todo_entry,
        create_journal_entry,
        list_writing_entries,
        search_entries,
        read_entry,
        complete_todo,
        get_incomplete_todos,
        get_todo_summary,
        add_task,
        update_entry,
        get_today
    ]

# ------- Execution Method -------
async def call_agent(query: str = "", selected_tools: list = []) -> str:
    tools = set(globals().get(tool) for tool in selected_tools)
    tools.add(get_now)
    tools.add(get_now_iso)

    model = OllamaModel(
        model_id='granite4:350m',
        host='http://localhost:11434'
    )

    system_prompt = """
    You are a precise personal assistant agent.

    When handling requests to create calendar events:
    1. CRITICAL!!!!!! ALWAYS call `get_now` or `get_now_iso` first to determine today's current date and time in ISO format.
    2. Convert relative terms like "today", "tomorrow", or "next Tuesday" into full dates (`YYYY-MM-DD`) based on the response from step 1.
    3. Convert 12-hour clock times (e.g., 4:30 PM, 5:30 PM) into 24-hour ISO timestamps (`YYYY-MM-DDTHH:MM:SS`).
       - Example: 4:30 PM becomes 16:30:00.
    4. Call `add_event` with:
       - `summary`: A concise event title (e.g., "Basketball Practice").
       - `start_time`: The complete start ISO string (e.g., "2026-07-25T16:30:00").
       - `end_time`: The complete end ISO string (e.g., "2026-07-25T17:30:00").
    5. Today's date is {}
    """.format(date.today())

    agent = Agent(
        model=model,
        tools=list(tools),
        system_prompt=system_prompt.strip()
    )

    try:
        print("Query handed to agent...")
        response = await agent.invoke_async(query)
        return response.message['content'][0]['text'] # type: ignore
    except Exception as e:
        return f"An error occurred when trying to call the agent: {e}"
