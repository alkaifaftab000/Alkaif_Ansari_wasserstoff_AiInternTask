import logging

from supabase_service import supabase, store_analysis_in_supabase, get_email_thread, get_attachments_by_email_id
from llama_api import summarize_text

def summarize_fetched_emails(emails, include_attachments):
    """
    Summarize emails by threading conversations and combining with extracted text from attachments.
    :param emails: List of email metadata dictionaries.
    :param include_attachments: Boolean flag indicating whether to include attachment text in the analysis.
    """
    logging.info("Starting summarization of fetched emails.")
    for email in emails:
        try:
            # Fetch the thread ID
            thread_id = email.get("threadId")
            email_id = email.get("id")

            # Fetch the entire thread if thread_id exists
            if thread_id:
                logging.info(f"Fetching thread for thread ID: {thread_id}")
                thread_emails = get_email_thread(thread_id)
                thread_content = "\n\n".join([e["body_text"] for e in thread_emails if e.get("body_text")])
            else:
                logging.warning(f"No thread ID for email ID: {email_id}. Processing as a single email.")
                thread_content = email.get("body_text", "").strip()

            # Combine thread content with extracted text from attachments
            combined_text = thread_content
            if include_attachments:
                attachments = get_attachments_by_email_id(email["id"])
                if attachments:
                    attachment_texts = [attachment["extracted_text"] for attachment in attachments if attachment.get("extracted_text")]
                    if attachment_texts:
                        combined_text += "\n\n" + "\n\n".join(attachment_texts)
                        logging.debug(f"Combined text for email ID {email_id}: {combined_text}")
                else:
                    logging.info(f"No attachments found for email ID: {email_id}")

            # Skip summarization if there's no valid content
            if not combined_text.strip():
                logging.warning(f"Email ID {email_id} has no valid content. Adding placeholder summary.")
                summary = {"structured_output": "No valid content to summarize."}
            else:
                # Summarize the combined text
                logging.info(f"Summarizing content for email ID {email_id}")
                summary = summarize_text(combined_text)

            # Parse structured output
            structured_output = summary.get("structured_output", "")
            insights = "No insights available."
            action_data = "No action data available."
            thread_context = "No thread context available."
            action_type = "No action type available."

            # Extract insights
            if "### INSIGHTS" in structured_output:
                insights_section = structured_output.split("### INSIGHTS")[1].split("###")[0].strip()
                insights = insights_section if insights_section else insights

            # Extract action data
            if "### ACTION_DATA" in structured_output:
                action_data_section = structured_output.split("### ACTION_DATA")[1].split("###")[0].strip()
                action_data = action_data_section if action_data_section else action_data

            # Extract thread context
            if "### THREAD_CONTEXT" in structured_output:
                thread_context_section = structured_output.split("### THREAD_CONTEXT")[1].split("###")[0].strip()
                thread_context = thread_context_section if thread_context_section else thread_context

            # Combine insights, action data, and thread context
            combined_insights = f"INSIGHTS:\n{insights}\n\nACTION_DATA:\n{action_data}\n\nTHREAD_CONTEXT:\n{thread_context}"

            # Prepare analysis data
            analysis_data = {
                "email_id": email["id"],  # Use the email UUID
                "thread_id": thread_id,
                "summary": structured_output,
                "action_type": action_type,
                "insights": combined_insights,
            }
            logging.debug(f"Inserting analysis data into Supabase: {analysis_data}")
            store_analysis_in_supabase(analysis_data)
            logging.info(f"Summarization completed for email ID {email_id}.")

        except Exception as e:
            logging.error(f"Error processing email ID {email.get('id', 'Unknown ID')}: {e}")

    logging.info("Summarization of fetched emails completed.")

def summarize_emails():
    """
    Fetch unsummarized emails from Supabase, summarize them, and store the results.
    """
    logging.info("Starting email summarization workflow.")
    try:
        # Fetch unsummarized emails from Supabase
        response = supabase.table("emails").select("*").eq("processed", False).execute()
        unsummarized_emails = response.data

        if not unsummarized_emails:
            logging.info("No unsummarized emails found.")
            return

        for email in unsummarized_emails:
            try:
                thread_id = email.get("thread_id")
                if thread_id:
                    # Fetch the entire thread
                    thread_emails = get_email_thread(thread_id)
                    thread_content = "\n\n".join([e["body_text"] for e in thread_emails if e.get("body_text")])
                    if not thread_content.strip():
                        logging.warning(f"Thread {thread_id} has no valid content. Adding placeholder summary.")
                        summary = {"structured_output": "No valid content to summarize."}
                    else:
                        summary = summarize_text(thread_content)

                    # Parse structured output
                    structured_output = summary.get("structured_output", "")
                    insights = "No insights available."  # Default fallback
                    action_data = "No action data available."
                    thread_context = "No thread context available."
                    action_type = "No action type available."

                    if "### ACTION_TYPE" in structured_output:
                        action_type_section = structured_output.split("### ACTION_TYPE")[1].split("###")[0].strip()
                        action_type = action_type_section if action_type_section else action_type
                    if "### INSIGHTS" in structured_output:
                        insights_section = structured_output.split("### INSIGHTS")[1].split("###")[0].strip()
                        insights = insights_section if insights_section else insights
                    if "### ACTION_DATA" in structured_output:
                        action_data_section = structured_output.split("### ACTION_DATA")[1].split("###")[0].strip()
                        action_data = action_data_section if action_data_section else action_data
                    if "### THREAD_CONTEXT" in structured_output:
                        thread_context_section = structured_output.split("### THREAD_CONTEXT")[1].split("###")[0].strip()
                        thread_context = thread_context_section if thread_context_section else thread_context

                    # Combine insights, action data, and thread context
                    combined_insights = f"INSIGHTS:\n{insights}\n\nACTION_DATA:\n{action_data}\n\nTHREAD_CONTEXT:\n{thread_context}"

                    # Use the correct UUID for email_id
                    analysis_data = {
                        "email_id": email["id"],
                        "thread_id": thread_id,
                        "summary": structured_output,
                        "action_type": action_type,
                        "insights": combined_insights,
                    }
                    logging.debug(f"Inserting analysis data into Supabase: {analysis_data}")
                    store_analysis_in_supabase(analysis_data)
                else:
                    logging.warning(f"Email {email['id']} has no thread ID. Skipping summarization.")
            except Exception as e:
                logging.error(f"Error processing email ID {email['id']}: {e}")

        logging.info("Summarization and analysis completed successfully.")
    except Exception as e:
        logging.error(f"Error during summarization workflow: {e}")

