"""
Supabase Service Module
- Handles storing email data in Supabase.
"""

import os
import mimetypes
from supabase import create_client, Client
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Add this class at the top after imports
class SupabaseService:
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    def fetch_calendar_actions(self):
        """Fetch pending calendar actions from analysis table"""
        try:
            response = self.supabase.table('analysis')\
                .select('*')\
                .in_('action_type', ['SCHEDULE_MEETING', 'SET_REMINDER'])\
                .eq('calendar_status', 'PENDING')\
                .execute()
            return response.data
        except Exception as e:
            logging.error(f"Error fetching calendar actions: {str(e)}")
            return []

    def update_calendar_action_status(self, action_id, status, message):
        """Update the status of a calendar action"""
        try:
            self.supabase.table('analysis')\
                .update({
                    'calendar_status': status,
                    'calendar_message': message,
                    'processed_at': datetime.now().isoformat()
                })\
                .eq('id', action_id)\
                .execute()
            logging.info(f"Updated calendar action {action_id} status to {status}")
        except Exception as e:
            logging.error(f"Error updating calendar action status: {str(e)}")

    def extract_action_data(self, text):
        """Extract action data from text"""
        try:
            # Find the Action Data section
            if 'Action Data:' not in text:
                return None
                
            action_section = text.split('Action Data:')[1].split('Thread Context:')[0]
            
            # Initialize action data
            action_data = {}
            
            # Extract key-value pairs
            lines = action_section.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Handle special cases
                    if key == 'participants':
                        # Convert string of emails to list
                        emails = [e.strip() for e in value.strip('[]').split(',') if '@' in e]
                        action_data[key] = emails
                    elif key == 'duration_minutes':
                        # Extract number from string like "60 (assuming a 1-hour meeting)"
                        try:
                            duration = int(''.join(filter(str.isdigit, value)))
                            action_data[key] = str(duration)
                        except ValueError:
                            action_data[key] = '60'  # Default to 60 minutes
                    else:
                        action_data[key] = value

            # Ensure required fields
            required_fields = ['date', 'time', 'title', 'description']
            if not all(field in action_data for field in required_fields):
                logging.warning(f"Missing required fields in action data: {action_data}")
                return None

            return action_data
        except Exception as e:
            logging.error(f"Error extracting action data: {str(e)}")
            return None

    def store_analysis_in_supabase(self, analysis_data):
        """Store email analysis with separate action data"""
        try:
            # Extract action data from insights
            insights = analysis_data.get("insights", "")
            action_type = analysis_data.get("action_type", "NO_ACTION")
            
            # Initialize action_data dictionary
            action_data = {}
            
            if action_type in ['SCHEDULE_MEETING', 'SET_REMINDER']:
                # Find the Action Data section
                if 'Action Data:' in insights:
                    action_section = insights.split('Action Data:')[1].split('Thread Context:')[0]
                    lines = action_section.strip().split('\n')
                    
                    for line in lines:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            # Handle special fields
                            if key == 'participants':
                                # Convert string representation of list to actual list
                                value = [email.strip() for email in value.strip('[]').split(',') 
                                       if '@' in email and email.strip()]
                            elif key == 'duration_minutes':
                                # Extract number from string like "60 (assuming a 1-hour meeting)"
                                try:
                                    value = str(int(''.join(filter(str.isdigit, value))))
                                except ValueError:
                                    value = '60'  # Default duration
                            elif key == 'date':
                                if value.lower() == 'today':
                                    value = datetime.now().strftime('%Y-%m-%d')
                                elif value.lower() == 'tomorrow':
                                    value = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                            elif key == 'time':
                                if value.lower() == 'now':
                                    value = datetime.now().strftime('%H:%M')
                                elif "o'clock" in value.lower():
                                    hour = int(''.join(filter(str.isdigit, value)))
                                    if 'night' in value.lower() or 'evening' in value.lower():
                                        hour += 12
                                    value = f"{hour:02d}:00"
                                
                            action_data[key] = value

            # Prepare analysis record with properly formatted action_data
            analysis_record = {
                "email_id": str(analysis_data["email_id"]),
                "thread_id": analysis_data.get("thread_id"),
                "summary": analysis_data["summary"],
                "insights": analysis_data["insights"],
                "action_type": action_type,
                "action_data": action_data if action_data else None,  # Store as JSONB
                "calendar_status": "PENDING" if action_type in ['SCHEDULE_MEETING', 'SET_REMINDER'] else None,
                "search_performed": analysis_data.get("search_performed", False),
                "search_query": analysis_data.get("search_query", ""),
                "search_results": analysis_data.get("search_results"),
                "search_answer": analysis_data.get("search_answer", ""),
                "slack_notification_sent": analysis_data.get("slack_notification_sent", False),
                "slack_channel": analysis_data.get("slack_channel"),
                "slack_message_id": analysis_data.get("slack_message_id")
            }

            # Insert into Supabase
            response = self.supabase.table("analysis").insert(analysis_record).execute()
            
            if response.data:
                logging.info(f"Analysis stored successfully for email: {analysis_data['email_id']}")
                logging.debug(f"Stored action_data: {action_data}")
                
                # Mark email as processed
                update_response = self.supabase.table("emails").update(
                    {"processed": True}
                ).eq("id", str(analysis_data["email_id"])).execute()
                
                if update_response.data:
                    logging.info(f"Email {analysis_data['email_id']} marked as processed")
                else:
                    logging.error(f"Failed to mark email {analysis_data['email_id']} as processed")
            else:
                logging.error(f"Failed to store analysis for email: {analysis_data['email_id']}")
                
        except Exception as e:
            logging.error(f"Error storing analysis: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

def email_exists(message_id):
    """
    Check if an email with the given message_id already exists in the database.
    :param message_id: The message ID of the email.
    :return: True if the email exists, False otherwise.
    """
    try:
        response = supabase.table("emails").select("id").eq("message_id", message_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error checking email existence: {e}")
        return False

def upload_attachment_to_bucket(filename: str, content: bytes) -> str | None:
    """
    Upload an attachment to the Supabase storage bucket with dynamic MIME type detection.
    
    :param filename: The name of the file to be stored (e.g., "report.pdf").
    :param content: The binary content of the file.
    :return: The public URL of the uploaded file, or None if upload fails.
    """
    try:
        bucket_name = "attachments"  # Ensure this bucket exists in Supabase
        bucket = supabase.storage.from_(bucket_name)  # Correctly access bucket

        # Debug logs
        print(f"Uploading file: {filename}")
        print(f"Content type: {type(content)}")
        print(f"Content size: {len(content)} bytes")

        # Determine MIME type dynamically
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = "application/octet-stream"  # Fallback for unknown types
        print(f"Detected MIME type: {mime_type}")

        # Ensure content is bytes
        if not isinstance(content, bytes):
            raise ValueError(f"Content must be bytes, got {type(content)}")

        # Upload the file
        file_path = f"{filename}"  # Use filename as path; add prefix if needed for uniqueness
        response = bucket.upload(file_path, content)  # Pass content directly (no BytesIO)

        # Debug log for upload response
        print(f"Upload response: {response}")

        # Get the public URL
        public_url = bucket.get_public_url(file_path)
        print(f"File uploaded successfully. Public URL: {public_url}")
        return public_url

    except Exception as e:
        print(f"Error uploading attachment {filename}: {e}")
        return None

def store_emails_in_supabase(emails):
    """
    Store a list of emails in Supabase.
    :param emails: List of email metadata dictionaries.
    """
    try:
        for email in emails:
            # Skip emails that already exist
            if email_exists(email["id"]):
                print(f"Email with message_id {email['id']} already exists. Skipping...")
                continue

            # Insert email metadata into the emails table
            email_data = {
                "message_id": email["id"],
                "thread_id": email["threadId"],
                "sender_email": email["sender"],
                "subject": email["subject"],
                "body_text": email["body"],
                "timestamp": email["timestamp"],
            }
            response = supabase.table("emails").insert(email_data).execute()
            email_id = response.data[0]["id"]  # Get the inserted email ID

            # Batch insert recipients into the email_recipients table
            recipients = []
            for recipient_type, recipient_list in email["recipients"].items():
                for recipient in recipient_list:
                    if recipient.strip():
                        recipients.append({
                            "email_id": email_id,
                            "recipient_email": recipient.strip(),
                            "recipient_type": recipient_type,
                        })
            if recipients:
                supabase.table("email_recipients").insert(recipients).execute()

            # Upload attachments to the storage bucket and insert metadata into the attachments table
            attachments = []
            for attachment in email.get("attachments", []):
                public_url = upload_attachment_to_bucket(attachment["filename"], attachment["content"])
                if public_url:
                    attachments.append({
                        "email_id": email_id,
                        "filename": attachment["filename"],
                        "content_type": attachment.get("content_type", None),
                        "size": len(attachment["content"]),
                        "storage_path": public_url,  # Store the public URL
                    })
            if attachments:
                supabase.table("attachments").insert(attachments).execute()
                print(f"Inserted {len(attachments)} attachments for email ID {email_id}")  # Debug log

        print("Emails successfully stored in Supabase.")
    except Exception as e:
        print(f"Error storing emails in Supabase: {e}")

def get_email_thread(thread_id):
    """
    Retrieve all emails in a thread from the database and reconstruct the conversation.
    :param thread_id: The thread ID of the email thread.
    :return: A list of emails in the thread, sorted by timestamp (ascending).
    """
    try:
        # Remove the 'ascending' parameter - ascending is default
        response = supabase.table("emails").select("*").eq("thread_id", thread_id).order("timestamp").execute()
        return response.data
    except Exception as e:
        print(f"Error retrieving email thread: {e}")
        return []

def get_email_uuid_by_message_id(message_id):
    """
    Get the UUID of an email with the given message_id.
    :param message_id: The message ID of the email.
    :return: The UUID of the email, or None if not found.
    """
    try:
        response = supabase.table("emails").select("id").eq("message_id", message_id).limit(1).execute()
        if response.data:
            return response.data[0]["id"]
        else:
            print(f"No email found with message_id: {message_id}")
            return None
    except Exception as e:
        print(f"Error getting email UUID for message_id {message_id}: {e}")
        return None

def extract_action_data(structured_output):
    """Extract action data from structured output"""
    try:
        # Split the output into sections
        sections = structured_output.split('###')
        for section in sections:
            if 'ACTION_DATA' in section:
                # Parse the action data section
                action_data = {}
                lines = section.strip().split('\n')[1:]  # Skip the header
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        action_data[key.strip()] = value.strip()
                return action_data
        return None
    except Exception as e:
        logging.error(f"Error extracting action data: {str(e)}")
        return None

def store_analysis_in_supabase(analysis_data):
    """Store email analysis with separate action data"""
    try:
        # Extract action data from insights if present
        action_data = extract_action_data(analysis_data.get("insights", ""))

        # Prepare analysis record
        analysis_record = {
            "email_id": str(analysis_data["email_id"]),
            "thread_id": analysis_data.get("thread_id"),
            "summary": analysis_data["summary"],
            "insights": analysis_data["insights"],
            "action_type": analysis_data["action_type"],
            "action_data": action_data,  # Store parsed action data
            "search_performed": analysis_data.get("search_performed", False),
            "search_query": analysis_data.get("search_query", ""),
            "search_results": analysis_data.get("search_results"),
            "search_answer": analysis_data.get("search_answer", ""),
            "slack_notification_sent": analysis_data.get("slack_notification_sent", False),
            "slack_channel": analysis_data.get("slack_channel"),
            "slack_message_id": analysis_data.get("slack_message_id")
        }

        response = supabase.table("analysis").insert(analysis_record).execute()
        
        if response.data:
            logging.info(f"Analysis stored successfully for email: {analysis_data['email_id']}")
            
            # Mark email as processed
            update_response = supabase.table("emails").update(
                {"processed": True}
            ).eq("id", str(analysis_data["email_id"])).execute()
            
            if update_response.data:
                logging.info(f"Email {analysis_data['email_id']} marked as processed")
            else:
                logging.error(f"Failed to mark email {analysis_data['email_id']} as processed")
        else:
            logging.error(f"Failed to store analysis for email: {analysis_data['email_id']}")
            
    except Exception as e:
        logging.error(f"Error storing analysis: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def store_extracted_text_in_supabase(attachment_id, extracted_text):
    """
    Store extracted text in the 'extracted_text' column of the 'attachments' table.
    """
    try:
        # Update the extracted_text in the attachments table
        response = supabase.table("attachments").update(
            {"extracted_text": extracted_text}
        ).eq("id", attachment_id).execute()

        # Proper success check
        if not response.data:  # If response.data is empty, the update failed
            logging.error(f"Failed to update extracted text for attachment ID: {attachment_id}")
        else:
            logging.info(f"Successfully updated extracted text for attachment ID: {attachment_id}")

        # Debug log to inspect the full response structure
        logging.debug(f"Supabase response: {vars(response)}")
    except Exception as e:
        logging.error(f"Error storing extracted text for attachment ID {attachment_id}: {str(e)}")

def get_attachments_by_email_id(email_id):
    """
    Fetch attachments for a given email ID from the database.
    :param email_id: The UUID of the email.
    :return: A list of attachments.
    """
    try:
        response = supabase.table("attachments").select("*").eq("email_id", email_id).execute()
        if response.data:
            logging.debug(f"Fetched {len(response.data)} attachments for email ID: {email_id}")
            return response.data
        else:
            logging.warning(f"No attachments found for email ID: {email_id}")
            return []
    except Exception as e:
        logging.error(f"Error fetching attachments for email ID {email_id}: {e}")
        return []


