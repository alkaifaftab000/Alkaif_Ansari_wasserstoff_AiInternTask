"""
Main Module
- Orchestrates the workflow for Gmail API, email parsing, and Supabase storage.
"""

import argparse
import logging
from gmail_service import authenticate_gmail, fetch_unread_emails, fetch_all_emails
from supabase_service import store_emails_in_supabase, supabase
from summarization_service import analyze_emails, analyze_email
from attachment_service import analyze_attachments
import os
import mimetypes
import tempfile
import requests
from docx import Document
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
import fitz  # PyMuPDF

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('email_processing.log'),
        logging.StreamHandler()
    ]
)

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

def process_emails(mode, batch_size):
    """
    Interactive email processing workflow
    """
    try:
        # Phase 1: Fetch and Store Emails
        logging.info(f"Phase 1: Starting email fetch with mode: {mode}, batch size: {batch_size}")
        service = authenticate_gmail()

        if mode == "unread":
            messages = fetch_unread_emails(service, max_results=batch_size)
        elif mode == "all":
            messages = fetch_all_emails(service, max_results=batch_size)
        else:
            logging.error(f"Invalid mode: {mode}")
            return

        if not messages:
            logging.info("No emails were fetched.")
            return

        # Store emails in Supabase
        stored_emails = store_emails_in_supabase(emails=messages)
        logging.info(f"Phase 1 Complete: {len(messages)} emails stored in Supabase.")

        # Phase 2: Attachment Processing (Optional)
        process_attachments = input("\nDo you want to process attachments? (yes/no): ").strip().lower()
        if process_attachments in ['yes', 'y']:
            logging.info("Phase 2: Starting attachment processing")
            analyze_attachments()
            logging.info("Phase 2 Complete: Attachments processed and summarized")
        else:
            logging.info("Skipping attachment processing")

        # Phase 3: Email Analysis
        analyze_emails_input = input("\nDo you want to analyze emails? (yes/no): ").strip().lower()
        if analyze_emails_input in ['yes', 'y']:
            logging.info("Phase 3: Starting email analysis")
            analyze_emails()
            logging.info("Phase 3 Complete: Emails analyzed")
        else:
            logging.info("Skipping email analysis")

        # Phase 4: Slack Notifications
        slack_notification_input = input("\nDo you want to process Slack notifications? (yes/no): ").strip().lower()
        if slack_notification_input in ['yes', 'y']:
            logging.info("Phase 4: Starting Slack notification processing")
            from summarization_service import process_slack_notifications
            process_slack_notifications()
            logging.info("Phase 4 Complete: Slack notifications processed")
        else:
            logging.info("Skipping Slack notifications")

        logging.info("Email processing workflow completed")

    except Exception as e:
        logging.error(f"Error in email processing workflow: {e}")
        import traceback
        logging.error(traceback.format_exc())

def analyze_attachments():
    """
    Process attachments and generate summaries
    """
    try:
        # Fetch attachments
        logging.info("Fetching attachments from Supabase...")
        response = supabase.table("attachments").select(
            "id",
            "email_id",
            "filename",
            "content_type",
            "storage_path"
        ).execute()
        
        attachments = response.data
        if not attachments:
            logging.info("No attachments found to process")
            return

        logging.info(f"Found {len(attachments)} attachments to process")
        processed_email_ids = {}  # Dictionary to store email_id -> summaries mapping

        for attachment in attachments:
            try:
                attachment_id = attachment.get("id")
                email_id = attachment.get("email_id")
                filename = attachment.get("filename")
                content_type = attachment.get("content_type")
                storage_path = attachment.get("storage_path")

                if not all([attachment_id, email_id, filename, storage_path]):
                    logging.warning(f"Skipping attachment {attachment_id}: Missing required fields")
                    continue

                logging.info(f"Processing attachment: {filename} (ID: {attachment_id})")

                # Create temp file with proper extension
                file_extension = os.path.splitext(filename)[1]
                if not file_extension and content_type:
                    ext = mimetypes.guess_extension(content_type)
                    if ext:
                        file_extension = ext

                temp_file_path = os.path.join(
                    tempfile.gettempdir(),
                    f"temp_{attachment_id}{file_extension}"
                )

                try:
                    # Download file
                    logging.info(f"Downloading file from {storage_path}")
                    response = requests.get(storage_path, timeout=30)
                    response.raise_for_status()

                    # Save to temp file
                    with open(temp_file_path, "wb") as temp_file:
                        temp_file.write(response.content)

                    # Extract text based on content type
                    extracted_text = None
                    if content_type == "application/pdf":
                        logging.info(f"Extracting text from PDF: {filename}")
                        extracted_text = extract_text_from_pdf(temp_file_path)
                    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        logging.info(f"Extracting text from DOCX: {filename}")
                        extracted_text = extract_text_from_doc(temp_file_path)
                    elif content_type and content_type.startswith("image/"):
                        logging.info(f"Extracting text from image: {filename}")
                        extracted_text = extract_text_from_image(temp_file_path)
                    else:
                        logging.warning(f"Unsupported content type: {content_type} for file: {filename}")
                        continue

                    if extracted_text and extracted_text.strip():
                        # Generate summary using NLTK
                        summary = summarize_text(extracted_text)
                        if summary:
                            if email_id not in processed_email_ids:
                                processed_email_ids[email_id] = []
                            processed_email_ids[email_id].append({
                                'filename': filename,
                                'summary': summary
                            })
                            logging.info(f"Generated summary for attachment: {filename}")

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        logging.debug(f"Cleaned up temp file: {temp_file_path}")

            except Exception as e:
                logging.error(f"Error processing attachment {filename}: {str(e)}")
                continue

        # Update email summaries
        for email_id, summaries in processed_email_ids.items():
            try:
                if summaries:
                    formatted_summaries = [
                        f"File: {s['filename']}\nSummary: {s['summary']}"
                        for s in summaries
                    ]
                    combined_summary = "\n\n".join(formatted_summaries)

                    logging.info(f"Updating attachment summary for email {email_id}")
                    response = supabase.table("emails").update({
                        "attachment_summary": combined_summary
                    }).eq("id", email_id).execute()

                    if response.data:
                        logging.info(f"Successfully updated summary for email {email_id}")
                    else:
                        logging.error(f"Failed to update summary for email {email_id}")

            except Exception as e:
                logging.error(f"Error updating summary for email {email_id}: {str(e)}")

        logging.info("Attachment processing completed")

    except Exception as e:
        logging.error(f"Error in attachment processing: {str(e)}")
        raise

def summarize_text(text, num_sentences=3):
    """
    Summarize text using NLTK
    """
    try:
        # Tokenize the text into sentences
        sentences = sent_tokenize(text)
        
        # If text is too short, return as is
        if len(sentences) <= num_sentences:
            return text

        # Tokenize words and remove stopwords
        stop_words = set(stopwords.words('english'))
        words = word_tokenize(text.lower())
        words = [word for word in words if word.isalnum() and word not in stop_words]

        # Calculate word frequencies
        freq_dist = FreqDist(words)

        # Score sentences based on word frequencies
        sentence_scores = {}
        for sentence in sentences:
            for word in word_tokenize(sentence.lower()):
                if word in freq_dist:
                    if sentence not in sentence_scores:
                        sentence_scores[sentence] = freq_dist[word]
                    else:
                        sentence_scores[sentence] += freq_dist[word]

        # Get top sentences
        summary_sentences = sorted(
            sentence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:num_sentences]

        # Sort sentences by their original order
        summary_sentences = sorted(
            summary_sentences,
            key=lambda x: sentences.index(x[0])
        )

        # Join sentences
        summary = ' '.join(sentence for sentence, score in summary_sentences)
        return summary

    except Exception as e:
        logging.error(f"Error in text summarization: {str(e)}")
        return None

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF using PyMuPDF
    """
    try:
        logging.info(f"Opening PDF with fitz: {file_path}")
        # Add debug logging
        logging.debug(f"Fitz version: {fitz.__version__}")
        
        with fitz.open(file_path) as pdf_document:
            text = ""
            for page_num in range(len(pdf_document)):
                text += pdf_document[page_num].get_text()
            
            # Log the first 100 characters of extracted text for verification
            preview = text[:100] + "..." if len(text) > 100 else text
            logging.info(f"Extracted text preview: {preview}")
            
            return text.strip() if text else None
            
    except Exception as e:
        logging.error(f"Error extracting text from PDF {file_path}: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def extract_text_from_doc(file_path):
    """
    Extract text from DOCX
    """
    try:
        logging.debug(f"Opening DOCX: {file_path}")
        doc = Document(file_path)
        text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
        return text.strip()
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {str(e)}")
        return None

def extract_text_from_image(file_path):
    """
    Extract text from image using OCR.space API
    """
    api_key = "K89980301088957"
    try:
        logging.debug(f"Processing image with OCR: {file_path}")
        with open(file_path, "rb") as image_file:
            response = requests.post(
                "https://api.ocr.space/parse/image",
                files={"file": image_file},
                data={"apikey": api_key, "language": "eng"},
                timeout=30
            )
        response.raise_for_status()
        result = response.json()
        
        if result.get("ParsedResults"):
            text = result["ParsedResults"][0]["ParsedText"].strip()
            return text if text else None
        return None
    except Exception as e:
        logging.error(f"Error extracting text from image: {str(e)}")
        return None

# Main entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Gmail emails.")
    parser.add_argument("--mode", type=str, default="unread", choices=["unread", "all"],
                        help="Mode to fetch emails: 'unread' (default) or 'all'.")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Number of emails to fetch per batch (default: 10).")
    args = parser.parse_args()

    process_emails(mode=args.mode, batch_size=args.batch_size)
