"""
Supabase Service Module
- Handles storing email data in Supabase.
"""

import os
import io
import mimetypes
from supabase import create_client, Client
# from supabase.storage import StorageFileAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def store_analysis_in_supabase(analysis_data):
    """
    Store email analysis (summary and insights) in the Supabase analysis table.
    """
    try:
        # Retrieve the correct UUID for the email
        email_uuid = get_email_uuid_by_message_id(analysis_data["email_id"])
        if not email_uuid:
            print(f"Cannot store analysis: No UUID found for message_id {analysis_data['email_id']}")
            return

        # Update the analysis_data with the correct email_id (UUID)
        analysis_data["email_id"] = email_uuid

        # Insert analysis data into the analysis table
        response = supabase.table("analysis").insert(analysis_data).execute()
        print(f"Analysis stored successfully for email UUID: {email_uuid}")

        # Mark the email as processed in the emails table
        supabase.table("emails").update({"processed": True}).eq("id", email_uuid).execute()
        print(f"Email UUID {email_uuid} marked as processed.")
    except Exception as e:
        print(f"Error storing analysis for email UUID {analysis_data['email_id']}: {e}")


