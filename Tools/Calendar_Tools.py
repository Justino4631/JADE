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

class GoogleCalendarTools():
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
        self.service = build("calendar", "v3", credentials=creds)
    
    def _get_now_iso(self):
        """Get the current time in LA"""
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    
    @tool
    def read_upcoming_events(self, max_results=5) -> list | None:
        """Read X number of upcoming events from the calendar"""
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

            events = events_result.get("items", [])

            if not events:
                print("No upcoming events found.")
                return

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
            return
    
    @tool
    def add_event(self, summary: str, description: str, start_time: str, end_time: str) -> str:
        """Add an event to the calendar based on a summary, description, start time and end time"""
        is_all_day = len(start_time) <= 10

        if is_all_day:
            event = {
                "summary": summary,
                "description": description,
                "start": {
                    "date": start_time 
                },
                "end": {
                    "date": end_time 
                }
            }
        else:
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
            return f"Success! Event created at link {created_event.get('htmlLink')} with ID {created_event.get('id')}"
        except Exception as e:
            return f"An error occurred while trying to add a calendar event: {e}"
    
    @tool
    def delete_event(self, event_id: str) -> str:
        """Delete an event from the calendar based on its ID"""
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return f"Success! Event with ID {event_id} has been deleted!"
        except Exception as e:
            return f"An error occurred while trying to delete an event: {e}"

    @tool
    def get_now(self) -> str:
        """Get the current time in LA"""
        return datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()

    @tool
    def get_events_and_ids(self) -> dict:
        """Return a dictionary of each event's summary and their ID and start time"""
        data = {}
        events = []
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
                print("No upcoming events found")
                return {}

            for event in events:
                data[f"{event.get('summary')}"] = (event['id'], event['start'].get('dateTime', event['start'].get('date')))
            return data
        except Exception as e:
            print(f"An error occurred: {e}")
            return {}

    def list_tools(self) -> list:
        return [self.read_upcoming_events, self.delete_event, self.add_event, self.get_now, self.get_events_and_ids]

def use_calendar_tools(message: str = "") -> str:
    calendar = GoogleCalendarTools()

    model = OllamaModel(
        model_id='granite4.1:8b',
        host='http://localhost:11434'
    )

    agent = Agent(
        model=model,
        system_prompt=(
            "You are a manager of Google calendar operating in Pacific Time (America/Los_Angeles). "
            "When trying to create an event, remember to use the get_now tool to get the current date and time. "
            "For ALL-DAY events, provide start_time and end_time strings in 'YYYY-MM-DD' format (where end_time is the next day). "
            "For TIMED events, provide strings in 'YYYY-MM-DDTHH:MM:SS' format without appending a 'Z'."
            "When trying to delete an event, use the get_events_and_ids tool to get the event names and times and correspond them with which id to input to the delete tool"
            "When trying to EDIT an event, first figure out which event it is, get the ID, delete it, and reschedule it. Keep the same name and description of the event, however."
            "The current year is 2026"
        ),
        tools=calendar.list_tools()
    )

    response = agent(message)
    try:
        return response.message['content'][0]['text'] #type: ignore
    except Exception as e:
        return f"An error occurred: {e}"