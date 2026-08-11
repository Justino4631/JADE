"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Google Calendar helper tools wrapped as callable `strands` tools.
"""

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

SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarTools:
    def __init__(self):
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        # Build the Google Calendar service client for subsequent calls
        self.service = build("calendar", "v3", credentials=creds)
    
    def _get_now_iso(self):
        """Get current time in ISO format for LA timezone."""
        # Use timezone-aware now then convert to ISO format for API queries
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    
    @tool
    def read_upcoming_events(self, max_results: int = 5) -> list | None:
        """
        Retrieves upcoming calendar events.
        
        Args:
            max_results: Maximum number of events to return.
        """
        # Collect simplified event dicts for the requested time window
        upcoming_events = []
        now = self._get_now_iso()

        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            # Extract events list or an empty list if none
            events = events_result.get("items", [])

            if not events:
                print("No upcoming events found.")
                return None

            # Normalize and gather id/start/summary for each returned event
            for event in events:
                start = event['start'].get("dateTime", event['start'].get("date"))
                data = {
                    "ID": event['id'],
                    "Start": start,
                    "Event": event.get('summary')
                }
                upcoming_events.append(data)
            return upcoming_events
        
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    @tool
    def add_event(self, summary: str, description: str, start_time: str, end_time: str) -> str:
        """
        Creates a new calendar event.

        Args:
            summary: Title of the event (e.g., "Guitar lesson").
            description: Brief description or empty string "" if none provided.
            start_time: ISO format 'YYYY-MM-DDTHH:MM:SS' (e.g., '2026-07-21T16:30:00').
            end_time: ISO format 'YYYY-MM-DDTHH:MM:SS' (e.g., '2026-07-21T17:30:00').
                      If no end time is specified, default to 1 hour after start_time.
        """
        # Decide whether the event is an all-day event by length of start string
        is_all_day = len(start_time) <= 10

        if is_all_day:
            event = {
                "summary": summary,
                "description": description,
                "start": {"date": start_time},
                "end": {"date": end_time}
            }
        else:
            # Clean trailing 'Z' (UTC designator) for API compatibility
            clean_start = start_time.rstrip('Z')
            clean_end = end_time.rstrip('Z')
            
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    'dateTime': clean_start,
                    'timeZone': 'America/Los_Angeles'
                },
                'end': {
                    'dateTime': clean_end,
                    'timeZone': 'America/Los_Angeles'
                }
            }

        try:
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            return f"Success! Event created: {created_event.get('htmlLink')} (ID: {created_event.get('id')})"
        except Exception as e:
            return f"Error adding event: {e}"
    
    @tool
    def delete_event(self, event_id: str) -> str:
        """
        Deletes an event by its ID. Look up event IDs using `get_events_and_ids` first.

        Args:
            event_id: Unique string ID of the event to delete.
        """
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return f"Success! Event ID {event_id} deleted."
        except Exception as e:
            # Return the error string rather than raising to keep tool-friendly output
            return f"Error deleting event: {e}"

    @tool
    def get_now(self) -> str:
        """
        Returns current ISO date and time for America/Los_Angeles.
        Use this to determine current date/time when parsing relative dates like 'today' or 'tomorrow'.
        """
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()

    @tool
    def get_events_and_ids(self) -> dict:
        """
        Returns a mapping of upcoming event names to their IDs and start times.
        Use this to find an event ID before deleting or editing an entry.
        """
        # Return a simple mapping of event summary -> (id, start)
        data = {}
        now = self._get_now_iso()

        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            if not events:
                return {}

            for event in events:
                data[f"{event.get('summary')}"] = (
                    event['id'], 
                    event['start'].get('dateTime', event['start'].get('date'))
                )
            return data
        except Exception as e:
            print(f"Error fetching event IDs: {e}")
            return {}

    def list_tools(self) -> list:
        return [
            self.read_upcoming_events, 
            self.delete_event, 
            self.add_event, 
            self.get_now, 
            self.get_events_and_ids
        ]

@tool
def use_calendar_tools(message: str = "") -> str:
    """
    Handles calendar actions (creating, listing, editing, or deleting events).
    """
    calendar = GoogleCalendarTools()

    model = OllamaModel(
        model_id='qwen2.5:1.5b',
        host='http://localhost:11434'
    )

    agent = Agent(
        model=model,
        system_prompt=(
            "You are a calendar assistant operating IN PACIFIC TIME (America/Los_Angeles).\n"
            "Follow these rules strictly:\n"
            "1. Current year is 2026.\n"
            "2. Always call `get_now` first to verify the current date/time when relative terms like 'today' or 'tomorrow' are used.\n"
            "3. Format all start_time and end_time strings as 'YYYY-MM-DDTHH:MM:SS' without trailing 'Z'.\n"
            "4. Convert 12-hour times to 24-hour times (e.g. 4:30 PM = 16:30:00, 5:30 PM = 17:30:00).\n"
            "4. If no end time is specified, default `end_time` to 1 hour after `start_time` (or 1 minute for reminders).\n"
            "5. Set `description` to a brief detail if provided; otherwise pass an empty string \"\".\n"
            "6. To EDIT an event: run `get_events_and_ids` to find the ID, delete it using `delete_event`, and recreate it using `add_event`."
            "7. Add an event or reminder using the add_event tool"
        ),
        tools=calendar.list_tools()
    )

    response = agent(message)
    try:
        return response.message['content'][0]['text']  # type: ignore
    except Exception as e:
        return f"An error occurred: {e}"

#use_calendar_tools("make an event on my Google calendar for tomorrow Wednesday, July the 22nd 2026 starting at 5:30pm and ending at 6:30pm go to basketball practice")