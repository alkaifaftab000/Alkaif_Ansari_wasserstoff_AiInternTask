# src/slack_service.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging
from dotenv import load_dotenv

class SlackNotificationService:
    def __init__(self):
        load_dotenv()
        self.client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
        # Get channel ID instead of name
        self.default_channel = self._get_channel_id('general')
        
        # Priority channel mapping
        self.priority_channels = {
            "high": "project",    # High priority goes to project channel
            "medium": "general",  # Medium priority goes to general channel
            "low": "random"       # Low priority goes to random channel
        }
        
    def _get_channel_id(self, channel_name):
        """Get channel ID from channel name"""
        try:
            result = self.client.conversations_list()
            for channel in result['channels']:
                if channel['name'] == channel_name:
                    return channel['id']
            return None
        except SlackApiError as e:
            logging.error(f"Error getting channel ID: {e.response['error']}")
            return None

    def format_email_notification(self, email_data, importance="medium"):
        """Format email data into a Slack message with proper formatting"""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📧 New {importance.upper()} Priority Email"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*From:*\n{email_data.get('sender', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Subject:*\n{email_data.get('subject', 'No Subject')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Content:*\n{email_data.get('body', 'No content')[:1000]}..."
                }
            }
        ]
        
        # Add summary if available
        if email_data.get('summary'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n{email_data['summary']}"
                }
            })
            
        return blocks

    def send_email_notification(self, email_data, importance="medium"):
        try:
            # Try to join the channel first
            self.client.conversations_join(channel=self.default_channel)
            
            # Then send the message
            blocks = self.format_email_notification(email_data, importance)
            response = self.client.chat_postMessage(
                channel=self.default_channel,
                blocks=blocks,
                text=f"New email notification"
            )
            return response['ts']
        except SlackApiError as e:
            logging.error(f"Slack error: {e.response['error']}")
            raise

    def _send_attachments(self, channel, attachments):
        """Send email attachments to Slack channel"""
        try:
            for attachment in attachments:
                self.client.files_upload_v2(
                    channel=channel,
                    file=attachment['content'],
                    filename=attachment['filename'],
                    initial_comment="📎 Email Attachment"
                )
        except SlackApiError as e:
            logging.error(f"Error sending attachment: {e.response['error']}")