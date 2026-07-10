import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# We use the full 'calendar' scope to allow reading, writing, and deleting.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Authenticates the user and returns the Google Calendar API service object."""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service

def read_upcoming_events(service, max_results=5):
    """Prints the start and name of the next N events on the user's primary calendar."""
    print(f"\n--- Fetching the next {max_results} upcoming events ---")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    try:
        events_result = service.events().list(
            calendarId="primary", 
            timeMin=now,
            maxResults=max_results, 
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(f"ID: {event['id']} | [{start}] {event.get('summary')}")
            
    except HttpError as error:
        print(f"An error occurred: {error}")

def add_event(service, summary, description, start_time, end_time):
    """Creates a new event on the primary calendar.
    Times must be in ISO format string: 'YYYY-MM-DDTHH:MM:SS'
    """
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': f'{start_time}Z',  # Assuming UTC 'Z' for simplicity
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': f'{end_time}Z',
            'timeZone': 'UTC',
        },
    }

    try:
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"\n[Success] Event created! Link: {created_event.get('htmlLink')}")
        print(f"Event ID: {created_event.get('id')}")
        return created_event.get('id')
    except HttpError as error:
        print(f"An error occurred: {error}")

def delete_event(service, event_id):
    """Deletes an event by its unique Google Calendar Event ID."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"\n[Success] Event with ID {event_id} has been deleted.")
    except HttpError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    # Initialize connection
    service = get_calendar_service()
    
    # 1. Read upcoming events
    read_upcoming_events(service, max_results=5)
    
    # 2. Add an event (Example: Tomorrow at 3:00 PM UTC)
    # Adjust dates as needed for your testing!
    print("\nCreating a test event...")
    event_id = add_event(
        service,
        summary="Coding Session with Python",
        description="Testing my new calendar automation script!",
        start_time="2026-07-09T15:00:00",
        end_time="2026-07-09T16:00:00"
    )
    
    # Refresh view to show it was added
    read_upcoming_events(service, max_results=5)
    
    # 3. Delete the event we just made (Uncomment below to test automatic deletion)
    # if event_id:
    #     delete_event(service, event_id)