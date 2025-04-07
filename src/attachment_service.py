import logging
import requests  # For OCR.space API and downloading files
import argparse
from docx import Document
from supabase_service import store_extracted_text_in_supabase, supabase  # Import helper functions
import os
import tempfile
import mimetypes  # For MIME type detection
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
import fitz  # Move this to the top with other imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('attachment_processing.log'),
        logging.StreamHandler()
    ]
)

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
            storage_path = attachment.get("storage_path", "").strip()
            content_type = attachment.get("content_type", "")
            
            # More detailed logging
            logging.info(f"\nProcessing attachment:")
            logging.info(f"ID: {attachment_id}")
            logging.info(f"Filename: {filename}")
            logging.info(f"Storage Path: {storage_path}")
            logging.info(f"Content Type: {content_type}")

            try:
                # Download the file
                temp_file_path = os.path.join(tempfile.gettempdir(), filename)
                logging.info(f"Downloading to: {temp_file_path}")
                
                with open(temp_file_path, "wb") as temp_file:
                    response = requests.get(storage_path, timeout=60)
                    response.raise_for_status()
                    temp_file.write(response.content)
                
                # Verify file was downloaded
                if os.path.exists(temp_file_path):
                    file_size = os.path.getsize(temp_file_path)
                    logging.info(f"File downloaded successfully. Size: {file_size} bytes")
                else:
                    logging.error("File download failed - file does not exist")
                    continue

                # Process based on content type
                extracted_text = None
                if "pdf" in content_type.lower():  # More flexible PDF detection
                    logging.info("Processing as PDF...")
                    extracted_text = extract_text_from_pdf(temp_file_path)
                    if extracted_text:
                        logging.info(f"Extracted {len(extracted_text)} characters from PDF")
                    else:
                        logging.error("PDF text extraction failed")
                
                # Store the extracted text
                if extracted_text:
                    store_extracted_text_in_supabase(attachment_id, extracted_text)
                    logging.info("Successfully stored extracted text in Supabase")
                else:
                    logging.error("No text was extracted to store")

            except requests.exceptions.RequestException as e:
                logging.error(f"Download error: {str(e)}")
            except Exception as e:
                logging.error(f"Processing error: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
            finally:
                # Cleanup
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    logging.info("Temporary file cleaned up")

    except Exception as e:
        logging.error(f"Main process error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF using PyMuPDF
    """
    try:
        logging.debug(f"Opening PDF: {file_path}")
        pdf_document = fitz.open(file_path)  # Use pdf_document instead of doc to avoid confusion
        text = ""
        try:
            for page_num in range(len(pdf_document)):
                text += pdf_document[page_num].get_text()
        finally:
            pdf_document.close()  # Ensure document is closed
        return text.strip() if text else None
    except Exception as e:
        logging.error(f"Error extracting text from PDF {file_path}: {str(e)}")
        return None

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
                timeout=60  # Increased timeout
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

def analyze_text_with_sumy(text):
    """
    Analyze text using sumy to generate a summary
    """
    if not text or len(text.strip()) == 0:
        logging.warning("Cannot analyze empty text")
        return ""
        
    try:
        # Create parser
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        
        # Initialize summarizer
        summarizer = LsaSummarizer(Stemmer("english"))
        summarizer.stop_words = get_stop_words("english")

        # Generate summary (3 sentences)
        summary_sentences = summarizer(parser.document, 3)
        if not summary_sentences:
            return ""
            
        return " ".join([str(sentence) for sentence in summary_sentences])
    except Exception as e:
        logging.error(f"Error analyzing text with sumy: {e}")
        return ""

def aggregate_attachment_summaries(email_id):
    """
    Get all attachment summaries for an email and combine them
    """
    try:
        # Get all attachments for this email
        response = supabase.table("attachments").select("*").eq("email_id", email_id).execute()
        attachments = response.data
        
        if not attachments:
            return None

        all_summaries = []
        for attachment in attachments:
            extracted_text = attachment.get("extracted_text")
            if extracted_text:
                summary = analyze_text_with_sumy(extracted_text)
                if summary:
                    all_summaries.append(f"File: {attachment['filename']}\nSummary: {summary}")

        if all_summaries:
            return "\n\n".join(all_summaries)
        return None
    except Exception as e:
        logging.error(f"Error aggregating summaries for email {email_id}: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze attachments or summarize emails.")
    parser.add_argument("--analyze-attachments", action="store_true", help="Analyze attachments in emails.")
    args = parser.parse_args()

    if args.analyze_attachments:
        logging.info("Analyzing attachments...")
        analyze_attachments()
    else:
        logging.info("Skipping attachment analysis.")