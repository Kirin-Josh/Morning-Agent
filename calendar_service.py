import datetime
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    token_data = os.getenv("GOOGLE_TOKEN")
    creds = Credentials.from_authorized_user_info(
        json.loads(token_data), SCOPES
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build('calendar', 'v3', credentials=creds)

def get_todays_events():
    service = get_calendar_service()
    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end = now.replace(hour=23, minute=59, second=59).isoformat() + 'Z'

    all_events = []
    calendars = service.calendarList().list().execute()
    
    for calendar in calendars['items']:
        events = service.events().list(
            calendarId=calendar['id'],
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        all_events.extend(events.get('items', []))

    all_events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
    return all_events

if __name__ == '__main__':
    events = get_todays_events()
    if not events:
        print('No events today')
    else:
        for event in events:
            time = event['start'].get('dateTime', 'All day')
            if 'T' in time:
                time = time[11:16]
            print(f"• {time} — {event['summary']}")
            
    service = get_calendar_service()
    calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        calendars.extend(response['items'])
        page_token = response.get('nextPageToken')
        if not page_token:
            break