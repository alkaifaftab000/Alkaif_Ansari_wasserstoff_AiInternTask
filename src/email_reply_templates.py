"""
Email Reply Templates and Helper Functions
"""

from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EmailReplyTemplates:
    @staticmethod
    def get_meeting_confirmation_template(context: Dict[str, Any]) -> str:
        """Template for meeting confirmation replies"""
        return f"""
        Dear {context['sender_name']},

        Thank you for your email regarding {context['original_subject']}.

        I have scheduled the meeting as requested:
        - Date: {context['meeting_date']}
        - Time: {context['meeting_time']}
        - Duration: {context['meeting_duration']} minutes
        - Location: {context['meeting_location']}

        Please let me know if you need to make any changes to the schedule.

        Best regards,
        [Your Name]
        """

    @staticmethod
    def get_reminder_confirmation_template(context: Dict[str, Any]) -> str:
        """Template for reminder confirmation replies"""
        return f"""
        Dear {context['sender_name']},

        Thank you for your email. I have set up a reminder as requested:
        - Date: {context['reminder_date']}
        - Time: {context['reminder_time']}
        - Title: {context['reminder_title']}
        - Description: {context['reminder_description']}

        You will receive a notification at the specified time.

        Best regards,
        [Your Name]
        """

    @staticmethod
    def get_general_reply_template(context: Dict[str, Any]) -> str:
        """Template for general email replies"""
        return f"""
        Dear {context['sender_name']},

        Thank you for your email regarding {context['original_subject']}.

        {context['reply_content']}

        Please let me know if you need any further assistance.

        Best regards,
        [Your Name]
        """

    @staticmethod
    def get_error_template(context: Dict[str, Any]) -> str:
        """Template for error notifications"""
        return f"""
        Dear {context['sender_name']},

        Thank you for your email. I encountered an issue while processing your request:

        {context['error_message']}

        I will retry the operation and keep you updated.

        Best regards,
        [Your Name]
        """

class ReplyGenerator:
    @staticmethod
    def generate_reply(context: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate an email reply based on the context and action type
        """
        try:
            action_type = context.get('action_type', 'GENERAL')
            
            if action_type == 'SCHEDULE_MEETING':
                body = EmailReplyTemplates.get_meeting_confirmation_template(context)
            elif action_type == 'SET_REMINDER':
                body = EmailReplyTemplates.get_reminder_confirmation_template(context)
            elif action_type == 'ERROR':
                body = EmailReplyTemplates.get_error_template(context)
            else:
                body = EmailReplyTemplates.get_general_reply_template(context)

            subject = f"Re: {context.get('original_subject', 'Your Email')}"

            return {
                'subject': subject,
                'body': body
            }
        except Exception as e:
            logging.error(f"Error generating reply: {str(e)}")
            return {
                'subject': "Error Processing Your Request",
                'body': EmailReplyTemplates.get_error_template({
                    'sender_name': context.get('sender_name', 'there'),
                    'error_message': str(e)
                })
            } 