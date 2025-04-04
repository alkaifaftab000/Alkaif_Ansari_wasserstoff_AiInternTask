"""
Email Parser Module
- Extracts and parses email content (HTML-to-text).
"""

import base64
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser  # Import dateutil for flexible timestamp parsing
import logging  # Import logging module

def format_timestamp(raw_timestamp):
    """
    Formats a raw timestamp string into the PostgreSQL-compatible format.
    :param raw_timestamp: The raw timestamp string from email headers.
    :return: The formatted timestamp string or None if formatting fails.
    """
    try:
        # Use dateutil.parser to handle various timestamp formats
        parsed_timestamp = parser.parse(raw_timestamp)
        # Format it to match PostgreSQL's expected format
        return parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S%z")
    except Exception as e:
        print(f"Error formatting timestamp: {e}")
        return None

def parse_email(email, gmail_service):
    """
    Parse an email object to extract required fields.
    :param email: The email object from Gmail API.
    :param gmail_service: The Gmail API service instance.
    :return: A dictionary containing parsed email fields.
    """
    logging.info(f"Parsing email ID: {email.get('id', 'Unknown ID')}")
    try:
        # Extract headers
        headers = {header['name']: header['value'] for header in email['payload']['headers']}
        sender = headers.get('From', 'Unknown Sender')
        recipients = {
            "to": headers.get('To', '').split(','),
            "cc": headers.get('Cc', '').split(','),
            "bcc": headers.get('Bcc', '').split(',')
        }
        subject = headers.get('Subject', 'No Subject')

        # Extract and format the timestamp
        raw_timestamp = headers.get('Date', 'Unknown Date')
        timestamp = format_timestamp(raw_timestamp)

        if not timestamp:
            raise ValueError("Invalid or missing timestamp.")

        # Extract body
        body = extract_email_body(email['payload'])

        # Extract attachments
        attachments = extract_attachments(email, gmail_service)

        # Add Email ID and Thread ID
        email_id = email.get('id', 'Unknown ID')
        thread_id = email.get('threadId', 'Unknown Thread ID')

        # Validate required fields
        if not sender or not recipients["to"] or not subject or not timestamp or not body:
            raise ValueError("Missing required email fields.")

        logging.info(f"Successfully parsed email ID: {email_id}")
        return {
            'id': email_id,
            'threadId': thread_id,
            'sender': sender,
            'recipients': recipients,
            'subject': subject,
            'timestamp': timestamp,
            'body': body,
            'attachments': attachments,
        }
    except Exception as e:
        logging.error(f"Error parsing email ID {email.get('id', 'Unknown ID')}: {e}")
        return None

def extract_email_body(payload):
    """
    Extract the email body from the payload, checking all parts recursively.
    :param payload: The payload object from the email.
    :return: The email body as plain text, HTML stripped of tags, or a placeholder for image-based content.
    """
    try:
        # Check if there's a direct body in the payload
        if 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        # If the payload has parts, traverse them recursively
        if 'parts' in payload:
            for part in payload['parts']:
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain':  # Plain text body
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif mime_type == 'text/html':  # HTML body
                    html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    return BeautifulSoup(html_content, 'html.parser').get_text()

                # Handle image-based content
                elif mime_type.startswith('image/'):
                    return "[Image-based content]"

                # Recursively check nested parts
                if 'parts' in part:
                    body = extract_email_body(part)
                    if body:  # If a valid body is found, return it
                        return body

        return "No body content found."
    except Exception as e:
        print(f"Error extracting body: {e}")
        return "Error extracting body."

def extract_attachments(email, gmail_service):
    """
    Extract attachments from the email.
    :param email: The email object from Gmail API.
    :param gmail_service: The Gmail API service instance.
    :return: A list of attachments with filenames and content.
    """
    logging.info(f"Extracting attachments for email ID: {email.get('id', 'Unknown ID')}")
    attachments = []
    try:
        if 'parts' in email['payload']:
            for part in email['payload']['parts']:
                if part['filename']:
                    attachment_id = part['body'].get('attachmentId')
                    if attachment_id:
                        attachment = gmail_service.users().messages().attachments().get(
                            userId='me',
                            messageId=email['id'],
                            id=attachment_id
                        ).execute()
                        data = base64.urlsafe_b64decode(attachment['data'])
                        attachments.append({
                            'filename': part['filename'],
                            'content_type': part.get('mimeType', 'application/octet-stream'),
                            'content': data
                        })
                        print(f"Extracted attachment: {part['filename']}")  # Debug log
        logging.info(f"Extracted {len(attachments)} attachments for email ID: {email.get('id', 'Unknown ID')}")
        return attachments
    except Exception as e:
        logging.error(f"Error extracting attachments for email ID {email.get('id', 'Unknown ID')}: {e}")
        return []
