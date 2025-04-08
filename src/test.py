import sys
import os
import logging
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from calender_services import CalendarService
from supabase_service import SupabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_calendar_integration():
    """Test calendar functionality with a sample event"""
    try:
        # Initialize services
        calendar_service = CalendarService()
        supabase_service = SupabaseService()

        # Test 1: Check existing calendar actions
        logging.info("\nTest 1: Checking existing calendar actions...")
        actions = supabase_service.fetch_calendar_actions()
        if actions:
            logging.info(f"Found {len(actions)} pending calendar actions")
            # Process each action
            for action in actions:
                logging.info(f"\nProcessing Action ID: {action['id']}")
                logging.info(f"Action Type: {action['action_type']}")
                action_data = action.get('action_data', {})
                
                if action_data:
                    logging.info(f"Processing action data: {action_data}")
                    
                    # Test actual calendar event creation
                    if action['action_type'] == 'SET_REMINDER':
                        # Convert reminder to calendar event format
                        if 'for_user' in action_data:
                            action_data['participants'] = [action_data['for_user']]
                        action_data['duration_minutes'] = '30'  # Default duration for reminders
                    
                    # Try to schedule the event
                    success, message = calendar_service.schedule_event(action_data)
                    logging.info(f"Event creation result: {success}, {message}")
                    
                    # Update the status in Supabase
                    status = "COMPLETED" if success else "FAILED"
                    supabase_service.update_calendar_action_status(
                        action['id'],
                        status,
                        message
                    )
                else:
                    logging.warning(f"No action data found for action {action['id']}")
        else:
            logging.info("No pending calendar actions found")

        # Test 2: Create a test event
        logging.info("\nTest 2: Creating test calendar event...")
        test_action_data = {
            'date': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'time': '14:00',
            'duration_minutes': '30',
            'title': 'Test Calendar Integration',
            'description': 'This is a test event',
            'location': 'virtual',
            'participants': ['test@example.com']
        }
        
        success, message = calendar_service.schedule_event(test_action_data)
        logging.info(f"Test event creation: {'Successful' if success else 'Failed'}")
        logging.info(f"Message: {message}")

        logging.info("\nCalendar integration test completed!")

    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        test_calendar_integration()
    except Exception as e:
        logging.error(f"Test execution failed: {str(e)}")
        sys.exit(1)