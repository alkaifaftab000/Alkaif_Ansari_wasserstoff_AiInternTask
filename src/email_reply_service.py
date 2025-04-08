"""
Enhanced Email Reply Service with retry mechanism and confirmation flow
"""

import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from datetime import datetime
from typing import Dict, Any, Optional
from email_reply_templates import ReplyGenerator
from supabase_service import SupabaseService
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EmailReplyService:
    def __init__(self, gmail_service):
        self.service = gmail_service
        self.supabase = SupabaseService()
        self.max_retries = 3
        self.retry_delay = 60  # seconds

    def get_email_details(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Fetch email details from Supabase using UUID"""
        try:
            response = self.supabase.table("emails").select(
                "id",
                "message_id",
                "thread_id",
                "sender_email",
                "sender_name",
                "subject",
                "body_text"
            ).eq("id", email_id).single().execute()
            
            return response.data if response.data else None
        except Exception as e:
            logging.error(f"Error fetching email details: {str(e)}")
            return None

    def get_analysis_details(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Fetch analysis details from Supabase"""
        try:
            response = self.supabase.table("analysis").select(
                "id",
                "action_type",
                "action_data",
                "summary",
                "insights"
            ).eq("id", analysis_id).single().execute()
            
            return response.data if response.data else None
        except Exception as e:
            logging.error(f"Error fetching analysis details: {str(e)}")
            return None

    def store_reply(self, email_id: str, analysis_id: str, subject: str, body: str) -> Optional[Dict[str, Any]]:
        """Store reply in email_replies table"""
        try:
            reply_data = {
                "email_id": email_id,
                "analysis_id": analysis_id,
                "subject": subject,
                "body": body,
                "status": "PENDING",
                "retry_count": 0
            }
            response = self.supabase.table("email_replies").insert(reply_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logging.error(f"Error storing reply: {str(e)}")
            return None

    def update_reply_status(self, reply_id: str, status: str, error_message: str = None) -> bool:
        """Update reply status in database"""
        try:
            update_data = {
                "status": status,
                "sent_at": datetime.now().isoformat() if status == "SENT" else None,
                "error_message": error_message
            }
            if status == "FAILED":
                update_data["retry_count"] = self.supabase.rpc(
                    "increment_retry_count",
                    {"reply_id": reply_id}
                ).execute()

            response = self.supabase.table("email_replies").update(update_data).eq("id", reply_id).execute()
            return bool(response.data)
        except Exception as e:
            logging.error(f"Error updating reply status: {str(e)}")
            return False

    def prepare_reply_context(self, email_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context for reply generation"""
        context = {
            "original_subject": email_data["subject"],
            "sender_name": email_data["sender_name"] or "there",
            "action_type": analysis_data["action_type"],
            "action_data": analysis_data["action_data"],
            "summary": analysis_data["summary"],
            "insights": analysis_data["insights"]
        }

        # Add specific action data based on action type
        if analysis_data["action_type"] == "SCHEDULE_MEETING":
            context.update(analysis_data["action_data"])
        elif analysis_data["action_type"] == "SET_REMINDER":
            context.update(analysis_data["action_data"])

        return context

    def create_reply_message(self, email_data: Dict[str, Any], reply_text: str, subject: str) -> Optional[Dict[str, Any]]:
        """Create Gmail API message object"""
        try:
            message = MIMEText(reply_text)
            message['to'] = email_data['sender_email']
            message['subject'] = subject
            
            if 'message_id' in email_data:
                message['In-Reply-To'] = email_data['message_id']
            if 'thread_id' in email_data:
                message['References'] = email_data['thread_id']
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            return {'raw': raw}
        except Exception as e:
            logging.error(f"Error creating message: {str(e)}")
            return None

    def send_reply(self, message: Dict[str, Any], require_confirmation: bool = True) -> bool:
        """Send reply with retry mechanism"""
        try:
            if require_confirmation:
                print("\nProposed Reply:")
                print("-" * 50)
                print(f"To: {message['to']}")
                print(f"Subject: {message['subject']}")
                print("\nBody:")
                print(base64.urlsafe_b64decode(message['raw'].encode()).decode())
                print("-" * 50)
                
                confirm = input("\nSend this reply? (yes/no): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    logging.info("Reply cancelled by user")
                    return False

            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logging.info(f"Reply sent successfully. Message ID: {sent_message['id']}")
            return True
        except Exception as e:
            logging.error(f"Error sending reply: {str(e)}")
            return False

    def process_reply(self, email_id: str, analysis_id: str, require_confirmation: bool = True) -> bool:
        """Process and send email reply with retry mechanism"""
        try:
            logging.info(f"Starting reply process for email_id: {email_id}, analysis_id: {analysis_id}")
            
            # Fetch required data
            email_data = self.get_email_details(email_id)
            analysis_data = self.get_analysis_details(analysis_id)

            if not email_data:
                logging.error(f"No email data found for email_id: {email_id}")
                return False
            if not analysis_data:
                logging.error(f"No analysis data found for analysis_id: {analysis_id}")
                return False

            logging.info(f"Retrieved email data: {email_data}")
            logging.info(f"Retrieved analysis data: {analysis_data}")

            # Prepare context and generate reply
            context = self.prepare_reply_context(email_data, analysis_data)
            logging.info(f"Prepared context: {context}")
            
            reply = ReplyGenerator.generate_reply(context)
            logging.info(f"Generated reply: {reply}")

            if not reply:
                logging.error("Failed to generate reply")
                return False

            # Store reply in database
            stored_reply = self.store_reply(email_id, analysis_id, reply['subject'], reply['body'])
            if not stored_reply:
                logging.error("Failed to store reply in database")
                return False
            logging.info(f"Stored reply in database: {stored_reply}")

            # Create and send message
            message = self.create_reply_message(email_data, reply['body'], reply['subject'])
            if not message:
                logging.error("Failed to create message")
                self.update_reply_status(stored_reply['id'], "FAILED", "Failed to create message")
                return False
            logging.info(f"Created message: {message}")

            # Send with retry mechanism
            for attempt in range(self.max_retries):
                try:
                    if self.send_reply(message, require_confirmation):
                        logging.info(f"Successfully sent reply on attempt {attempt + 1}")
                        self.update_reply_status(stored_reply['id'], "SENT")
                        return True
                except Exception as e:
                    logging.error(f"Error on attempt {attempt + 1}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        logging.warning(f"Retry attempt {attempt + 1} of {self.max_retries}")
                        time.sleep(self.retry_delay)

            # If all retries failed
            error_msg = f"Failed after {self.max_retries} attempts"
            logging.error(error_msg)
            self.update_reply_status(stored_reply['id'], "FAILED", error_msg)
            return False

        except Exception as e:
            logging.error(f"Error in process_reply: {str(e)}")
            if stored_reply:
                self.update_reply_status(stored_reply['id'], "FAILED", str(e))
            return False