import datetime
import json
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    token_path = os.path.join(BASE_DIR, 'token.json')
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    return build('calendar', 'v3', credentials=creds)
# def get_calendar_service():
#     creds = None
#     token_path = os.path.join(BASE_DIR, 'token.json')
#     creds_path = os.path.join(BASE_DIR, 'credentials.json')
    
#     if os.path.exists(token_path):
#         creds = Credentials.from_authorized_user_file(token_path, SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
#             creds = flow.run_local_server(port=0)
#         with open(token_path, 'w') as token:
#             token.write(creds.to_json())
#     return build('calendar', 'v3', credentials=creds)

def get_todays_events():
    service = get_calendar_service()
    now = datetime.datetime.utcnow()
    start = now.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
    end = now.replace(hour=23, minute=59, second=59).isoformat() + 'Z'

    # Fetch ALL calendars with pagination
    all_calendars = []
    page_token = None
    while True:
        response = service.calendarList().list(pageToken=page_token).execute()
        all_calendars.extend(response['items'])
        page_token = response.get('nextPageToken')
        if not page_token:
            break

    all_events = []
    for calendar in all_calendars:
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