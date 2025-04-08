"""
Test file for Phase 6 - Auto-Reply Generation
Tests different scenarios for email reply generation and sending
"""

import unittest
import logging
from unittest.mock import patch, MagicMock
from email.mime.text import MIMEText
from typing import Dict, Any, Optional
from email_reply_service import EmailReplyService
from email_reply_templates import EmailReplyTemplates, ReplyGenerator
from supabase_service import SupabaseService
from datetime import datetime
import re
import dns.resolver

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def validate_email(email: str) -> bool:
    """Validate email format and domain
    
    Args:
        email (str): Email address to validate
        
    Returns:
        bool: True if email is valid and domain accepts email, False otherwise
    """
    # First check email format
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
        
    # Then check domain MX records
    try:
        domain = email.split('@')[1]
        mx_records = dns.resolver.resolve(domain, 'MX')
        
        # Check if there are any MX records
        if not mx_records:
            logging.warning(f"Domain {domain} has no MX records")
            return False
            
        # Check if any MX record has a preference of 0 (Null MX)
        for mx in mx_records:
            if mx.preference == 0:
                logging.warning(f"Domain {domain} has Null MX record (does not accept email)")
                return False
                
        return True
    except dns.resolver.NXDOMAIN:
        logging.warning(f"Domain {domain} does not exist")
        return False
    except dns.resolver.NoAnswer:
        logging.warning(f"No MX records found for domain {domain}")
        return False
    except Exception as e:
        logging.error(f"Error checking MX records for {domain}: {str(e)}")
        return False

class TestEmailReplyService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.mock_gmail_service = MagicMock()
        self.mock_supabase = MagicMock()
        self.service = EmailReplyService(self.mock_gmail_service)
        self.service.supabase = self.mock_supabase
        
        # Use valid test email domains
        self.test_sender = "sender@gmail.com"
        self.test_recipient = "recipient@gmail.com"

    def test_phase6_workflow(self):
        """Test the complete Phase 6 workflow"""
        # Mock email data with valid email addresses
        email_data = {
            'id': 'test-email-1',
            'message_id': 'test-message-1',
            'thread_id': 'test-thread-1',
            'sender_email': self.test_sender,
            'sender_name': 'Test Sender',
            'subject': 'Meeting Request',
            'body_text': 'Please schedule a meeting'
        }

        # Mock analysis data with valid participants
        analysis_data = {
            'id': 'test-analysis-1',
            'action_type': 'SCHEDULE_MEETING',
            'action_data': {
                'meeting_time': '2024-04-10T10:00:00',
                'meeting_duration': 60,
                'meeting_title': 'Test Meeting',
                'participants': [self.test_recipient]
            },
            'summary': 'Meeting request for Test Meeting',
            'insights': 'High priority meeting'
        }

        # Mock database responses
        self.mock_supabase.table().select().eq().single().execute.return_value.data = email_data
        self.mock_supabase.table().select().eq().single().execute.return_value.data = analysis_data

        # Test the complete workflow
        success = self.service.process_reply(
            email_id='test-email-1',
            analysis_id='test-analysis-1',
            require_confirmation=True
        )

        self.assertTrue(success)

    def test_phase6_error_handling(self):
        """Test error handling in Phase 6"""
        # Mock database responses to return None for missing data
        self.mock_supabase.table().select().eq().single().execute.return_value.data = None

        # Test error handling
        success = self.service.process_reply(
            email_id=None,
            analysis_id='test-analysis-1',
            require_confirmation=True
        )

        self.assertFalse(success)

    def test_phase6_retry_mechanism(self):
        """Test retry mechanism in Phase 6"""
        # Mock email data
        email_data = {
            'id': 'test-email-1',
            'sender_email': self.test_sender,
            'sender_name': 'Test Sender',
            'subject': 'Test Subject',
            'body_text': 'Test Body'
        }

        # Mock analysis data
        analysis_data = {
            'id': 'test-analysis-1',
            'action_type': 'SCHEDULE_MEETING',
            'action_data': {
                'meeting_time': '2024-04-10T10:00:00',
                'meeting_duration': 60,
                'meeting_title': 'Test Meeting',
                'participants': [self.test_recipient]
            },
            'summary': 'Test Summary',
            'insights': 'Test Insights'
        }

        # Mock database responses
        self.mock_supabase.table().select().eq().single().execute.return_value.data = email_data

        # Test retry mechanism
        success = self.service.process_reply(
            email_id='test-email-1',
            analysis_id='test-analysis-1',
            require_confirmation=True
        )

        self.assertTrue(success)

    def test_email_validation(self):
        """Test email validation"""
        # Test valid email
        self.assertTrue(validate_email("test@gmail.com"))
        
        # Test invalid emails
        self.assertFalse(validate_email("invalid-email"))
        self.assertFalse(validate_email("test@invalid"))
        self.assertFalse(validate_email("@domain.com"))

    def create_reply_message(self, email_data: Dict[str, Any], reply_text: str) -> Optional[Dict[str, Any]]:
        """Create Gmail API message object"""
        try:
            # Validate recipient email
            if not validate_email(email_data['sender_email']):
                logging.error(f"Invalid recipient email: {email_data['sender_email']}")
                return None
                
            message = MIMEText(reply_text)
            message['to'] = email_data['sender_email']
            message['subject'] = f"Re: {email_data['subject']}"
            
            if 'message_id' in email_data:
                message['In-Reply-To'] = email_data['message_id']
            if 'thread_id' in email_data:
                message['References'] = email_data['thread_id']
            
            return {'raw': message.as_string()}
        except Exception as e:
            logging.error(f"Error creating reply message: {str(e)}")
            return None

if __name__ == '__main__':
    unittest.main()