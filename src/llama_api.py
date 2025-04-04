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
        """

        # Payload for the API
        payload = {
            "model": "meta-llama/llama-3-8b-instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "max_tokens": 500,
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
