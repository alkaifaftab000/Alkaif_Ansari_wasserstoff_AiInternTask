# """
# Test Script for Gmail API Integration
# - Fetches emails and verifies that all required fields are parsed correctly.
# """

# from gmail_service import authenticate_gmail, fetch_all_emails

# def test_fetch_emails():
#     """
#     Test fetching and parsing emails, including attachments.
#     """
#     # Authenticate Gmail API
#     service = authenticate_gmail()

#     # Fetch unread emails (you can switch to fetch_all_emails if needed)
#     emails = fetch_all_emails(service, max_results=1)

#     # Print the parsed email data
#     for email in emails:
#         print("Email ID:", email.get('id'))
#         print("Thread ID:", email.get('threadId'))
#         print("Sender:", email.get('sender'))
#         # print("Recipient:", email.get('recipient', 'Unknown Recipient'))
#         print("Subject:", email.get('subject'))
#         print("Timestamp:", email.get('timestamp', 'Unknown Timestamp'))
#         print("Body:", email.get('body'))
#         print("Attachments:")
#         for attachment in email.get('attachments', []):
#             print(f"  - Filename: {attachment['filename']}")
#             print(f"  - Content (truncated): {attachment['content'][:50]}...")  # Print first 50 characters
#         print("-" * 50)

# if __name__ == "__main__":
#     test_fetch_emails()
#=====================================================================================================#


# Test script for thread reconstruction
# Pick a thread_id from your database
# from supabase_service import get_email_thread
# sample_thread_id = "195f4d5eb2de12fa"

# # Get all emails in the thread
# thread_emails = get_email_thread(sample_thread_id)

# # Print the thread to verify
# print(f"Found {len(thread_emails)} emails in thread {sample_thread_id}")
# for i, email in enumerate(thread_emails):
#     print(f"\nEmail {i+1}:")
#     print(f"From: {email['sender_email']}")
#     print(f"Subject: {email['subject']}")
#     print(f"Date: {email['timestamp']}")
#     print(f"First 100 chars: {email['body_text'][:100]}...")

#=======================================================================
# Test script for OpenRouter API
import requests

API_KEY = "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"
api_url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "meta-llama/llama-3-8b-instruct",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant that summarizes emails and provides actionable insights."},
        {"role": "user", "content": "This is a test email content to summarize."}
    ],
    "max_tokens": 300,
    "temperature": 0.7
}

response = requests.post(api_url, json=payload, headers=headers)

if response.status_code == 200:
    print("API Test Successful!")
    print(response.json())
else:
    print(f"API Test Failed: {response.status_code}")
    print(response.text)