"""
Main Module
- Orchestrates the workflow for Gmail API, email parsing, and Supabase storage.
"""

import argparse
import logging
from gmail_service import authenticate_gmail, fetch_unread_emails, fetch_all_emails
from supabase_service import store_emails_in_supabase
from summarization_service import summarize_fetched_emails, summarize_emails
from attachment_service import analyze_attachments  # Import the new service for attachment analysis

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_emails(mode, batch_size):
    """
    Fetch emails from Gmail, store them in Supabase, and optionally summarize them.
    """
    logging.info(f"Starting email processing workflow with mode: {mode}, batch size: {batch_size}")
    service = authenticate_gmail()

    # Fetch emails based on the mode
    if mode == "unread":
        messages = fetch_unread_emails(service, max_results=batch_size)
    elif mode == "all":
        messages = fetch_all_emails(service, max_results=batch_size)
    else:
        logging.error(f"Invalid mode: {mode}")
        return

    if messages:
        # Store emails in Supabase
        store_emails_in_supabase(emails=messages)  # Pass the messages to store_emails_in_supabase
        logging.info(f"{len(messages)} emails have been successfully fetched and stored in Supabase.")

        # Ask the user if they want to analyze attachments
        user_input = input("Do you want to analyze attachments? (yes/no): ").strip().lower()
        analyze_attachments_flag = user_input in ["yes", "y"]

        if analyze_attachments_flag:
            logging.info("Analyzing attachments...")
            analyze_attachments()  # Call analyze_attachments without arguments
        else:
            logging.info("Skipping attachment analysis.")

        # Ask the user if they want to proceed with summarization
        user_input = input("Do you want to proceed with summarization? (yes/no): ").strip().lower()
        if user_input in ["yes", "y"]:
            summarize_fetched_emails(messages, analyze_attachments_flag)  # Pass the flag to summarization
        else:
            logging.info("Exiting without summarization.")
    else:
        logging.info("No emails were fetched.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Gmail emails.")
    parser.add_argument("--mode", type=str, default="unread", choices=["unread", "all"],
                        help="Mode to fetch emails: 'unread' (default) or 'all'.")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Number of emails to fetch per batch (default: 10).")
    args = parser.parse_args()

    process_emails(mode=args.mode, batch_size=args.batch_size)
