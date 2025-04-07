# test_slack.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
from slack_service import SlackNotificationService

def test_slack_connection():
    load_dotenv()
    client = WebClient(token=os.getenv('SLACK_BOT_TOKEN'))
    
    try:
        # Test API call
        response = client.auth_test()
        print("Successfully connected to Slack!")
        print(f"Connected as: {response['user']}")
        print(f"To workspace: {response['team']}")
        
        # List channels (to test permissions)
        channels = client.conversations_list()
        print("\nAccessible channels:")
        for channel in channels['channels']:
            print(f"- {channel['name']}")
            
    except SlackApiError as e:
        print(f"Error: {e.response['error']}")

def test_slack_notification():
    # Sample email data that should trigger a Slack notification
    sample_email = {
        'sender': 'test@example.com',
        'subject': 'Test Email for Slack Notification',
        'body': 'This is a test email to verify Slack notification functionality.',
        'summary': 'Test summary for Slack notification.'
    }

    # Initialize SlackNotificationService
    slack_service = SlackNotificationService()

    # Send notification to Slack
    try:
        message_id = slack_service.send_email_notification(sample_email, importance="high")
        print(f"Slack notification sent successfully. Message ID: {message_id}")
    except Exception as e:
        print(f"Error sending Slack notification: {e}")

def test_slack_setup():
    """Test Slack channel setup and permissions"""
    slack = SlackNotificationService()
    channel_id = slack._get_channel_id('general')
    print(f"Channel ID for #general: {channel_id}")
    
    try:
        # Try joining the channel
        slack.client.conversations_join(channel=channel_id)
        print("Successfully joined #general")
    except SlackApiError as e:
        print(f"Error joining channel: {e.response['error']}")

def test_notification():
    """Test sending a notification"""
    slack = SlackNotificationService()
    test_data = {
        'sender': 'test@example.com',
        'subject': 'Test Notification',
        'body': 'This is a test notification',
        'summary': 'Test summary'
    }
    try:
        slack.send_email_notification(test_data)
        print("Test notification sent successfully")
    except Exception as e:
        print(f"Error sending test notification: {str(e)}")

if __name__ == "__main__":
    test_slack_connection()
    test_slack_notification()
    test_slack_setup()
    test_notification()