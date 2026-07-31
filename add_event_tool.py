import datetime
import os
from zoneinfo import ZoneInfo
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def init_google_calendar():
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

def parse_to_la_naive(iso_str: str) -> str:
    """Parses any valid ISO string and converts it to a naive LA local time string."""
    tz = ZoneInfo("America/Los_Angeles")
    
    # Python 3.11+ handles 'Z' and offset strings like '-07:00' natively
    dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    
    # If a timezone offset was provided, convert to LA time and remove timezone info
    if dt.tzinfo is not None:
        dt = dt.astimezone(tz).replace(tzinfo=None)
        
    return dt.strftime('%Y-%m-%dT%H:%M:%S')


def add_event(summary: str, start_time: str, end_time: str) -> str:
    """Creates a new Google Calendar event."""
    is_all_day = len(start_time) <= 10

    if is_all_day:
        event = {
            "summary": summary,
            "description": "",
            "start": {"date": start_time},
            "end": {"date": end_time}
        }
    else:
        formatted_start = parse_to_la_naive(start_time)
        formatted_end = parse_to_la_naive(end_time)

        event = {
            "summary": summary,
            "description": "",
            "start": {
                'dateTime': formatted_start,
                'timeZone': 'America/Los_Angeles'
            },
            'end': {
                'dateTime': formatted_end,
                'timeZone': 'America/Los_Angeles'
            }
        }

    try:
        created_event = SERVICE.events().insert(calendarId='primary', body=event).execute()
        return f"Success! Event created: {created_event.get('htmlLink')} (ID: {created_event.get('id')})"
    except Exception as e:
        return f"Error adding event: {e}"

# This will now work whether you pass offsets or plain strings:
print(add_event("Test", start_time='2026-07-28T16:30:00-06:00', end_time='2026-07-28T17:30:00-06:00'))