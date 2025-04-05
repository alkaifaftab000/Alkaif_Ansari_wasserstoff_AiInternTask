import logging
import fitz  # PyMuPDF
import requests  # For OCR.space API and downloading files
import argparse
from docx import Document
from supabase_service import store_extracted_text_in_supabase, supabase  # Import helper functions
import os
import tempfile
import mimetypes  # For MIME type detection

def analyze_attachments():
    """
    Fetch attachments with NULL extracted_text, process them, and store the extracted text in Supabase.
    """
    try:
        # Fetch all attachments where extracted_text is NULL
        response = supabase.table("attachments").select("*").is_("extracted_text", None).execute()
        attachments = response.data

        if not attachments:
            logging.info("No attachments found for analysis.")
            return

        logging.info(f"Found {len(attachments)} attachments for analysis.")

        for attachment in attachments:
            attachment_id = attachment.get("id")
            filename = attachment.get("filename", "Unknown")
            storage_path = attachment.get("storage_path", "").strip()  # Sanitize storage_path
            content_type = attachment.get("content_type", "")
            extracted_text = ""
            temp_file_path = None  # Initialize temp_file_path to None

            try:
                # Log the storage_path for debugging
                logging.debug(f"Processing attachment ID: {attachment_id}, filename: {filename}")
                logging.debug(f"Fetched storage_path: {storage_path}")

                # Validate storage_path
                if not storage_path or not storage_path.startswith(("http://", "https://")):
                    logging.warning(f"Attachment {filename} has an invalid storage path: {storage_path}. Skipping...")
                    continue

                # Download the file from the public URL
                temp_file_path = os.path.join(tempfile.gettempdir(), filename)  # Keep original filename
                with open(temp_file_path, "wb") as temp_file:
                    response = requests.get(storage_path)
                    response.raise_for_status()  # Raise an error for HTTP issues
                    temp_file.write(response.content)

                # Validate the downloaded file
                file_size = os.path.getsize(temp_file_path)
                mime_type, _ = mimetypes.guess_type(temp_file_path)
                logging.debug(f"Downloaded file: {temp_file_path}, Size: {file_size} bytes, MIME Type: {mime_type}")

                if file_size == 0 or not mime_type or mime_type not in ["image/jpeg", "image/png", "application/pdf"]:
                    logging.error(f"Unsupported file type for OCR: {temp_file_path}")
                    continue

                # Process the downloaded file
                if content_type == "application/pdf":
                    extracted_text = extract_text_from_pdf(temp_file_path)
                elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    extracted_text = extract_text_from_doc(temp_file_path)
                elif content_type.startswith("image/"):
                    extracted_text = extract_text_from_image(temp_file_path)
                else:
                    logging.warning(f"Unsupported attachment type: {content_type}")

                # Store the extracted text back in the attachments table
                if extracted_text:
                    store_extracted_text_in_supabase(attachment_id, extracted_text)
                    logging.info(f"Extracted text stored for attachment ID: {attachment_id}, filename: {filename}")
            except Exception as e:
                logging.error(f"Error processing attachment ID {attachment_id}, filename: {filename}: {e}")
            finally:
                # Clean up the temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

    except Exception as e:
        logging.error(f"Error fetching attachments for analysis: {e}")

def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF file using PyMuPDF (fitz).
    """
    try:
        doc = fitz.open(file_path)
        return " ".join(page.get_text() for page in doc)
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_doc(file_path):
    """
    Extract text from a DOCX file.
    """
    try:
        doc = Document(file_path)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_image(file_path):
    """
    Extract text from an image file using the OCR.space API.
    """
    api_key = "K89980301088957"  # Replace with your actual API key
    try:
        # Log file details
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        logging.debug(f"Processing image file: {file_path}, Size: {file_size} bytes, MIME Type: {mime_type}")

        # Validate file size and MIME type
        if not mime_type or mime_type not in ["image/jpeg", "image/png"]:
            logging.error(f"Unsupported file type for OCR: {file_path}")
            return ""

        with open(file_path, "rb") as image_file:
            response = requests.post(
                "https://api.ocr.space/parse/image",
                files={"file": (os.path.basename(file_path), image_file)},  # Pass original filename
                data={"apikey": api_key},
            )
        response.raise_for_status()  # Raise an error for HTTP issues

        # Log the full API response for debugging
        result = response.json()
        logging.debug(f"OCR.space API response: {result}")

        # Check for errors in the API response
        if result.get("IsErroredOnProcessing"):
            error_message = result.get("ErrorMessage", ["Unknown error"])[0]
            logging.error(f"OCR.space API error: {error_message}")
            return ""

        # Extract and return the parsed text
        parsed_text = result.get("ParsedResults", [{}])[0].get("ParsedText", "")
        if not parsed_text.strip():
            logging.info(f"No text found in image: {file_path}")  # Not an error
        return parsed_text
    except Exception as e:
        logging.error(f"Error extracting text from image: {e}")
        return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze attachments or summarize emails.")
    parser.add_argument("--analyze-attachments", action="store_true", help="Analyze attachments in emails.")
    args = parser.parse_args()

    if args.analyze_attachments:
        logging.info("Analyzing attachments...")
        analyze_attachments()
    else:
        logging.info("Skipping attachment analysis.")