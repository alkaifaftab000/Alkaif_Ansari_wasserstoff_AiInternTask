import logging

import supabase
from supabase_service import store_analysis_in_supabase, get_email_thread
from llama_api import summarize_text

def summarize_fetched_emails(emails):
    """
    Summarize the emails that were just fetched and store the results in Supabase.
    """
    logging.info("Starting summarization of fetched emails.")
    for email in emails:
        try:
            thread_id = email.get("threadId")
            if thread_id:
                # Fetch the entire thread
                thread_emails = get_email_thread(thread_id)
                logging.debug(f"Fetched emails for thread ID {thread_id}: {thread_emails}")
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

                # Use the correct UUID for email_id
                analysis_data = {
                    "email_id": email["id"],  # Pass the message_id here
                    "thread_id": thread_id,
                    "summary": structured_output,
                    "action_type": action_type,
                    "insights": combined_insights,  # Store combined insights, action data, and thread context
                }
                logging.debug(f"Inserting analysis data into Supabase: {analysis_data}")
                store_analysis_in_supabase(analysis_data)
            else:
                # Summarize the single email
                if not email.get("body_text", "").strip():
                    logging.warning(f"Email {email['id']} has no valid content. Adding placeholder summary.")
                    summary = {"structured_output": "No valid content to summarize."}
                else:
                    logging.debug(f"Summarizing single email ID: {email['id']}")
                    summary = summarize_text(email["body_text"])

                # Parse structured output
                structured_output = summary.get("structured_output", "")
                insights = "No insights available."  # Default fallback
                action_data = "No action data available."
                thread_context = "No thread context available."

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

                # Use the correct UUID for email_id
                analysis_data = {
                    "email_id": email["id"],  # Pass the message_id here
                    "thread_id": thread_id,
                    "summary": structured_output,
                    "insights": combined_insights,  # Store combined insights, action data, and thread context
                }
                logging.debug(f"Inserting analysis data into Supabase: {analysis_data}")
                store_analysis_in_supabase(analysis_data)
            logging.info(f"Summarization completed for email ID {email['id']}.")

        except Exception as e:
            logging.error(f"Error processing email ID {email['id']}: {e}")

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

