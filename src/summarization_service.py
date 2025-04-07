import logging

from supabase_service import supabase, store_analysis_in_supabase, get_email_thread, get_attachments_by_email_id, get_email_uuid_by_message_id
from llama_api import summarize_text

__all__ = ['analyze_emails', 'analyze_email']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_analysis.log'),
        logging.StreamHandler()
    ]
)

def get_email_content_for_analysis(email_id):
    """
    Get all content for analysis including email body, subject, and attachment summaries
    """
    try:
        # Get email details
        response = supabase.table("emails").select("*").eq("id", email_id).execute()
        if not response.data:
            logging.error(f"No email found with ID: {email_id}")
            return None

        email = response.data[0]
        content = {
            "subject": email.get("subject", "No Subject"),
            "body": email.get("body_text", ""),
            "attachment_summary": email.get("attachment_summary", ""),
            "thread_id": email.get("thread_id")
        }

        # Get thread content if exists
        thread_id = email.get("thread_id")
        if thread_id:
            thread_emails = get_email_thread(thread_id)
            thread_content = "\n\n".join([e["body_text"] for e in thread_emails if e.get("body_text")])
            content["thread_content"] = thread_content

        logging.debug(f"Retrieved content for email {email_id}: {content}")
        return content
    except Exception as e:
        logging.error(f"Error getting email content for {email_id}: {e}")
        return None

def prepare_analysis_input(content):
    """
    Prepare the input text for LLaMA analysis
    """
    try:
        # Combine all content with clear section markers
        analysis_input = f"""
SUBJECT: {content['subject']}

BODY: {content['body']}

ATTACHMENT SUMMARY: {content['attachment_summary']}
"""
        if 'thread_content' in content:
            analysis_input += f"\nTHREAD CONTENT: {content['thread_content']}"

        logging.debug("Prepared analysis input with all content sections")
        return analysis_input.strip()
    except Exception as e:
        logging.error(f"Error preparing analysis input: {e}")
        return None

def parse_llama_response(structured_output):
    """
    Parse the structured output from LLaMA API
    """
    try:
        result = {
            "summary": "",
            "insights": "",
            "action_type": "NO_ACTION",
            "action_data": "",
            "thread_context": "",
            "search_required": False,
            "search_query": "",
            "context_needed": ""
        }

        # Extract summary
        if "### SUMMARY" in structured_output:
            summary_section = structured_output.split("### SUMMARY")[1].split("###")[0].strip()
            result["summary"] = summary_section

        # Extract insights
        if "### INSIGHTS" in structured_output:
            insights_section = structured_output.split("### INSIGHTS")[1].split("###")[0].strip()
            result["insights"] = insights_section

        # Extract action type
        if "### ACTION_TYPE" in structured_output:
            action_type_section = structured_output.split("### ACTION_TYPE")[1].split("###")[0].strip()
            result["action_type"] = action_type_section

        # Extract action data
        if "### ACTION_DATA" in structured_output:
            action_data_section = structured_output.split("### ACTION_DATA")[1].split("###")[0].strip()
            result["action_data"] = action_data_section

        # Extract thread context
        if "### THREAD_CONTEXT" in structured_output:
            thread_context_section = structured_output.split("### THREAD_CONTEXT")[1].split("###")[0].strip()
            result["thread_context"] = thread_context_section

        # Extract search required
        if "### SEARCH_REQUIRED" in structured_output:
            search_section = structured_output.split("### SEARCH_REQUIRED")[1].split("###")[0].strip()
            for line in search_section.split('\n'):
                if 'required:' in line:
                    result["search_required"] = 'true' in line.lower()
                elif 'search_query:' in line:
                    result["search_query"] = line.split('search_query:')[1].strip()
                elif 'context_needed:' in line:
                    result["context_needed"] = line.split('context_needed:')[1].strip()

        logging.debug(f"Parsed LLaMA response: {result}")
        return result
    except Exception as e:
        logging.error(f"Error parsing LLaMA response: {e}")
        return None

def analyze_email(message_id):
    """
    Analyze a single email including its attachments and thread
    """
    try:
        logging.info(f"Starting analysis for message ID: {message_id}")

        # Get email details using the message_id
        response = supabase.table("emails").select("*").eq("message_id", message_id).execute()
        if not response.data:
            logging.error(f"No email found with message_id: {message_id}")
            return

        email = response.data[0]
        email_uuid = email["id"]  # Get the UUID from the database
        
        # Get all content for analysis
        content = {
            "subject": email.get("subject", "No Subject"),
            "body": email.get("body_text", ""),
            "attachment_summary": email.get("attachment_summary", ""),
            "thread_id": email.get("thread_id"),
            "sender_email": email.get("sender_email")
        }

        # Prepare input for LLaMA
        analysis_input = prepare_analysis_input(content)
        if not analysis_input:
            return

        # Get analysis from LLaMA
        logging.info(f"Sending content to LLaMA for analysis")
        llama_response = summarize_text(analysis_input)
        if not llama_response:
            logging.error("No response from LLaMA")
            return

        # Parse the response
        analysis_result = parse_llama_response(llama_response.get("structured_output", ""))
        if not analysis_result:
            return

        # Combine insights, action data, and thread context into a single insights field
        combined_insights = f"""
Insights:
{analysis_result["insights"]}

Action Data:
{analysis_result["action_data"]}

Thread Context:
{analysis_result["thread_context"]}
"""

        # Prepare analysis data
        analysis_data = {
            "email_id": email_uuid,
            "thread_id": content["thread_id"],
            "summary": analysis_result["summary"],
            "insights": combined_insights.strip(),
            "action_type": analysis_result["action_type"],
            "search_performed": False,
            "search_query": "",
            "search_results": None,
            "search_answer": "",
            "slack_notification_sent": False,
            "slack_channel": None,
            "slack_message_id": None
        }

        # Handle Slack notifications if action type is FORWARD_TO_SLACK
        if analysis_result["action_type"] == "FORWARD_TO_SLACK":
            try:
                from slack_service import SlackNotificationService
                slack_service = SlackNotificationService()
                
                # Prepare email data for Slack
                email_data = {
                    'sender': content['sender_email'],
                    'subject': content['subject'],
                    'body': content['body'],
                    'summary': analysis_result['summary'],
                    'attachments': [] if content.get('attachment_summary') != 'true' else content.get('attachments', [])
                }
                
                # Send to Slack
                message_id = slack_service.send_email_notification(
                    email_data=email_data,
                    importance=content.get('importance', 'medium'),
                    mentions=content.get('mention_users', '').split(',') if content.get('mention_users') != 'none' else None
                )
                
                # Update analysis data with Slack information
                analysis_data.update({
                    'slack_notification_sent': True,
                    'slack_channel': content.get('importance'),
                    'slack_message_id': message_id
                })
                
                logging.info(f"Slack notification sent successfully to channel {content.get('importance')}")
                
            except Exception as e:
                logging.error(f"Failed to send Slack notification: {str(e)}")
                analysis_data['slack_notification_sent'] = False

        # Handle web search if required
        if analysis_result["search_required"]:
            logging.info("Web search required, performing search...")
            from web_search_service import perform_web_search, analyze_search_results
            
            # Perform web search
            search_results = perform_web_search(analysis_result["search_query"])
            if search_results:
                # Analyze search results
                search_answer = analyze_search_results(
                    search_results,
                    analysis_result["context_needed"]
                )
                
                # Update analysis data with search results
                analysis_data.update({
                    "search_performed": True,
                    "search_query": analysis_result["search_query"],
                    "search_results": search_results,
                    "search_answer": search_answer
                })

        # Store in analysis table
        store_analysis_in_supabase(analysis_data)
        logging.info(f"Analysis completed for message ID: {message_id}")

    except Exception as e:
        logging.error(f"Error analyzing email {message_id}: {e}")
        import traceback
        logging.error(traceback.format_exc())

def analyze_emails():
    """
    Analyze all unprocessed emails
    """
    logging.info("Starting email analysis workflow")
    try:
        # Get unprocessed emails
        response = supabase.table("emails").select(
            "id",  # This is the UUID
            "message_id",  # This is the Gmail message ID
            "subject",
            "body_text",
            "attachment_summary",
            "thread_id",
            "processed"
        ).eq("processed", False).execute()
        
        unprocessed_emails = response.data
        if not unprocessed_emails:
            logging.info("No unprocessed emails found")
            return

        logging.info(f"Found {len(unprocessed_emails)} unprocessed emails")
        
        for email in unprocessed_emails:
            try:
                # Convert message_id to UUID format
                message_id = email.get("message_id")
                if not message_id:
                    logging.error("Email missing message_id, skipping...")
                    continue
                    
                # Get the UUID using message_id
                email_uuid = get_email_uuid_by_message_id(message_id)
                if not email_uuid:
                    logging.error(f"Could not find UUID for message_id: {message_id}")
                    continue
                
                # Analyze using the proper UUID
                analyze_email(message_id)
            except Exception as e:
                logging.error(f"Error processing email: {e}")
                continue

        logging.info("Email analysis workflow completed")
    except Exception as e:
        logging.error(f"Error in email analysis workflow: {e}")
        import traceback
        logging.error(traceback.format_exc())

if __name__ == "__main__":
    analyze_emails()

