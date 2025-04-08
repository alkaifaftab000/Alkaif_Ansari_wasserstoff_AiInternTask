from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging
import json
import os.path
import pickle

class CalendarService:
    def __init__(self):
        self.creds = None
        self.service = None
        self.setup_credentials()

    def setup_credentials(self):
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        
        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists('config/token.pickle'):
            with open('config/token.pickle', 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                credentials_path = 'D:/Intern/wassersoft innovation/Smart_Email_Analyzer/config/google_calender_credentials.json'
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('config/token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.creds = creds
            self.service = build('calendar', 'v3', credentials=creds)
            logging.info("Calendar credentials setup successful")
        except Exception as e:
            raise Exception(f"Failed to setup calendar credentials: {str(e)}")

    def check_availability(self, start_time, duration_minutes):
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            return len(events_result.get('items', [])) == 0
        except Exception as e:
            print(f"Error checking availability: {str(e)}")
            return False

    def find_next_available_slot(self, start_time, duration_minutes):
        current_slot = start_time
        max_attempts = 5  # Look for next 5 possible slots

        for _ in range(max_attempts):
            if self.check_availability(current_slot, duration_minutes):
                return current_slot
            current_slot += timedelta(hours=1)
        return None

    def schedule_event(self, action_data):
        try:
            logging.info(f"Scheduling event with data: {action_data}")

            # Parse and standardize date
            date_str = action_data['date']
            if date_str.lower() == 'today':
                date_str = datetime.now().strftime('%Y-%m-%d')
            elif date_str.lower() == 'tomorrow':
                date_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'th' in date_str.lower():
                # Handle "10th April 2025" format
                date_str = datetime.strptime(date_str, "%dth %B %Y").strftime('%Y-%m-%d')

            # Parse and standardize time
            time_str = action_data['time']
            if time_str.lower() in ['none', 'now', 'not specified']:
                time_str = datetime.now().strftime('%H:%M')
            elif 'pm' in time_str.lower():
                # Convert "2:00 PM" to "14:00"
                time_obj = datetime.strptime(time_str, '%I:%M %p')
                time_str = time_obj.strftime('%H:%M')
            elif "o'clock" in time_str.lower():
                # Handle "9 o'clock at night"
                hour = int(''.join(filter(str.isdigit, time_str)))
                if any(word in time_str.lower() for word in ['night', 'evening', 'pm']):
                    hour += 12 if hour != 12 else 0
                time_str = f"{hour:02d}:00"

            # Create datetime object with timezone
            start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            local_tz = datetime.now().astimezone().tzinfo
            start_time = start_time.replace(tzinfo=local_tz)

            # Set duration (default 60 minutes if not specified)
            duration = int(action_data.get('duration_minutes', 60))

            # Create event body
            event = {
                'summary': action_data['title'],
                'description': action_data.get('description', 'No description provided'),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC'
                },
                'end': {
                    'dateTime': (start_time + timedelta(minutes=duration)).isoformat(),
                    'timeZone': 'UTC'
                },
                'location': action_data.get('location', 'virtual')
            }

            # Add attendees if available
            if 'participants' in action_data and action_data['participants']:
                if isinstance(action_data['participants'], list):
                    attendees = [{'email': email} for email in action_data['participants']]
                else:
                    # Handle single email as string
                    attendees = [{'email': action_data['participants']}]
                event['attendees'] = attendees

            # Add reminders
            event['reminders'] = {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30}
                ]
            }

            logging.info(f"Creating event with data: {event}")
            created_event = self.service.events().insert(calendarId='primary', body=event).execute()
            
            return True, f"Event created successfully. Event ID: {created_event.get('id')}"
        except Exception as e:
            logging.error(f"Error scheduling event: {str(e)}")
            return False, f"Failed to schedule event: {str(e)}"