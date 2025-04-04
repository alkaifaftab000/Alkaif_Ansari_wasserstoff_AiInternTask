"""
Gmail Service Module
- Handles Gmail API authentication and email fetching.
"""

import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email_parser import parse_email  # Import the updated parse_email function

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2 and return a service object.
    """
    logging.info("Authenticating with Gmail API...")
    creds = None
    token_path = os.path.join('config', 'token.json')
    credentials_path = os.path.join('config', 'credentials.json')

    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logging.info("Refreshed expired credentials.")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
                logging.info("New credentials obtained.")

            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
                logging.info("Credentials saved to token.json.")

        logging.info("Authentication successful.")
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        logging.error(f"Error during Gmail authentication: {e}")
        raise

def fetch_unread_emails(service, max_results=10):
    """
    Fetch unread emails from Gmail, parse them, and return a list of parsed email data.
    """
    return fetch_emails(service, query='is:unread', max_results=max_results)

def fetch_all_emails(service, max_results=10):
    """
    Fetch all emails (read and unread) from Gmail, parse them, and return a list of parsed email data.
    """
    return fetch_emails(service, query='', max_results=max_results)

def fetch_emails(service, query, max_results=10):
    """
    Fetch emails from Gmail based on a query, parse them, and return a list of parsed email data.
    """
    logging.info(f"Fetching emails with query: {query}, max_results: {max_results}")
    try:
        parsed_emails = []
        page_token = None

        while True:
            # Fetch email metadata (IDs) with pagination
            results = service.users().messages().list(
                userId='me', labelIds=['INBOX'], q=query, maxResults=max_results, pageToken=page_token
            ).execute()
            messages = results.get('messages', [])
            page_token = results.get('nextPageToken')

            for message in messages:
                # Fetch full email details using the message ID
                email = service.users().messages().get(userId='me', id=message['id']).execute()
                
                # Parse the email using the updated parse_email function
                parsed_email = parse_email(email, service)
                if parsed_email:
                    parsed_emails.append(parsed_email)

            if not page_token:
                break

        logging.info(f"Successfully fetched {len(parsed_emails)} emails.")
        return parsed_emails
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []
