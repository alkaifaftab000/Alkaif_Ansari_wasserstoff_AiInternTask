import requests
import logging

# OpenRouter API key
API_KEY = "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"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def summarize_text(text):
    """
    Summarize the given text using the OpenRouter API with Llama 3B.
    :param text: The text to summarize.
    :return: A dictionary containing the summary, insights, and actionable data.
    """
    logging.info("Sending text to OpenRouter API for summarization.")
    try:
        # Ensure the text is not empty
        if not text.strip():
            raise ValueError("Text for summarization is empty.")

        # OpenRouter API endpoint
        api_url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        # Prompt to guide the Llama 3B model
        system_prompt = """
        You are an email processing assistant. Analyze the email content and provide a structured output that can be parsed programmatically. Format your response EXACTLY as follows:

        ### SUMMARY
        - [3-5 bullet points summarizing key information, each 20-30 words maximum]

        ### INSIGHTS
        [Brief actionable insights about the email content, maximum 100 words]

        ### ACTION_TYPE
        [EXACTLY ONE of: SCHEDULE_MEETING, SEND_REPLY, SET_REMINDER, FORWARD_TO_SLACK, NO_ACTION]

        ### ACTION_DATA
        If ACTION_TYPE is SCHEDULE_MEETING:
        date: [extract date from email otherwise use "today"]
        time: [extract time from email otherwise use "now"]
        duration_minutes: [integer]
        participants: [comma separated emails]
        title: [meeting title]
        description: [brief meeting description]
        location: [meeting location or "virtual"]

        If ACTION_TYPE is SEND_REPLY:
        recipients: [comma separated emails]
        cc: [comma separated emails or "none"]
        subject: [reply subject]
        message: [reply text, maximum 100 words]
        priority: [low, normal, high]

        If ACTION_TYPE is SET_REMINDER:
        date: [extract date from email otherwise use "today"]
        time: [extract time from email otherwise use "now"]
        title: [reminder title]
        description: [reminder details]
        for_user: [email of user to remind]

        If ACTION_TYPE is FORWARD_TO_SLACK:
        channel: [slack channel name]
        importance: [low, medium, high]
        mention_users: [comma separated usernames or "none"]
        message: [information to share]
        include_attachment: [true or false]

        If ACTION_TYPE is NO_ACTION:
        reason: [brief explanation]

        ### THREAD_CONTEXT
        thread_requires_attention: [true or false]
        previous_communications: [integer number of previous emails in thread]
        response_urgency: [low, medium, high]
        key_stakeholders: [comma separated emails of important people in thread]

        ### SEARCH_REQUIRED
        required: [true/false]
        search_query: [extracted search terms]
        context_needed: [what kind of information we're looking for]
        """

        # Payload for the API
        payload = {
            "model": "meta-llama/llama-3-8b-instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": 2000,
            "temperature": 0.7
        }

        # Log the payload for debugging
        logging.debug(f"Payload sent to OpenRouter API: {payload}")

        # Make the API request
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()

        # Parse the response
        result = response.json()
        logging.debug(f"Full API response: {result}")  # Log the full API response for debugging

        structured_output = result.get("choices", [{}])[0].get("message", {}).get("content", "No structured output available.")

        logging.info("Summarization successful.")
        return {"structured_output": structured_output}
    except requests.exceptions.RequestException as e:
        logging.error(f"Error summarizing text: {e}")
        return {"structured_output": "Error generating structured output."}

def update_email_attachment_summary(email_id, summary):
    """
    Update the attachment_summary column in the emails table
    """
    try:
        response = supabase.table("emails").update(
            {"attachment_summary": summary}
        ).eq("id", email_id).execute()
        
        if response.data:
            logging.info(f"Updated attachment_summary for email {email_id}")
        else:
            logging.error(f"Failed to update attachment_summary for email {email_id}")
    except Exception as e:
        logging.error(f"Error updating attachment_summary: {e}")

def process_email_attachments(email_id):
    """
    Process all attachments for an email and update the email's attachment_summary
    """
    try:
        # Get combined summary of all attachments
        combined_summary = aggregate_attachment_summaries(email_id)
        
        if combined_summary:
            # Update email's attachment_summary
            update_email_attachment_summary(email_id, combined_summary)
            logging.info(f"Processed attachments for email {email_id}")
        else:
            logging.info(f"No attachment summaries generated for email {email_id}")
    except Exception as e:
        logging.error(f"Error processing email attachments: {e}")

def analyze_attachments():
    """
    Main function to process attachments and update email summaries
    """
    try:
        # First, process any unprocessed attachments
        response = supabase.table("attachments").select("*").is_("extracted_text", None).execute()
        attachments = response.data

        if not attachments:
            logging.info("No new attachments to process")
            return

        logging.info(f"Found {len(attachments)} attachments to process")

        # Track which emails need summary updates
        processed_email_ids = set()

        # Process each attachment
        for attachment in attachments:
            try:
                # ... (existing attachment processing code) ...

                # If text was extracted successfully, add email_id to processed set
                if extracted_text:
                    processed_email_ids.add(attachment["email_id"])
            except Exception as e:
                logging.error(f"Error processing attachment: {e}")

        # Update summaries for all affected emails
        for email_id in processed_email_ids:
            process_email_attachments(email_id)

    except Exception as e:
        logging.error(f"Error in analyze_attachments: {e}")

def generate_email_reply(context):
    """Generate email reply using LLaMA"""
    try:
        prompt = f"""
        Generate a professional email reply based on the following context:
        
        Original Subject: {context['original_subject']}
        Action Type: {context['action_type']}
        Recipient Name: {context['sender_name']}
        
        Action Details:
        {context['action_details']}
        
        Requirements:
        1. Start with a professional greeting using the recipient's name
        2. Acknowledge the original email
        3. Confirm the action taken (meeting scheduled or reminder set)
        4. Provide relevant details (date, time, location)
        5. End with a professional closing
        6. Keep the tone friendly but professional
        7. Be concise but informative
        
        Format the response as a complete email message.
        """

        response = summarize_text(prompt)
        if response and "structured_output" in response:
            return response["structured_output"]
        return None
    except Exception as e:
        logging.error(f"Error generating email reply: {str(e)}")
        return None
