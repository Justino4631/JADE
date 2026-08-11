"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Utilities to add events to Google Calendar and helper time parsing.
"""

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
    """Parse an ISO datetime string and return a naive LA-local time string.

    This accepts strings with 'Z' or explicit offsets and normalizes them
    into a timezone-naive string in America/Los_Angeles for calendar APIs.
    """
    tz = ZoneInfo("America/Los_Angeles")
    
    # Normalize a trailing 'Z' to a +00:00 offset so fromisoformat works.
    dt = datetime.datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    
    # If the parsed datetime has tzinfo, convert into LA and drop tzinfo
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
        # Convert incoming ISO strings into naive LA-local datetimes
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