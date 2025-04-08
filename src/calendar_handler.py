import logging
from supabase_service import SupabaseService
from calender_services import CalendarService
from datetime import datetime

def is_valid_email(email):
    """Check if email is in valid format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

class CalendarHandler:
    def __init__(self):
        self.supabase_service = SupabaseService()
        self.calendar_service = CalendarService()

    def process_calendar_actions(self):
        try:
            actions = self.supabase_service.fetch_calendar_actions()
            if not actions:
                logging.info("No pending calendar actions found")
                return []

            results = []
            for action in actions:
                try:
                    action_data = action.get('action_data', {})
                    if not action_data:
                        logging.warning(f"No action data found for action {action['id']}")
                        continue

                    # Validate and clean participants/attendees
                    if 'participants' in action_data:
                        if isinstance(action_data['participants'], list):
                            action_data['participants'] = [
                                email for email in action_data['participants'] 
                                if is_valid_email(email)
                            ]
                    elif 'for_user' in action_data:
                        if is_valid_email(action_data['for_user']):
                            action_data['participants'] = [action_data['for_user']]
                        else:
                            action_data['participants'] = []

                    # Handle date/time formats
                    if action_data['time'].lower() == 'none' or action_data['time'].lower() == 'not specified':
                        action_data['time'] = datetime.now().strftime('%H:%M')

                    if 'th' in action_data['date']:
                        # Convert "10th April 2025" to "2025-04-10"
                        try:
                            date_obj = datetime.strptime(action_data['date'], "%dth %B %Y")
                            action_data['date'] = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            action_data['date'] = datetime.now().strftime("%Y-%m-%d")

                    logging.info(f"Processing calendar action: {action['id']}")
                    logging.info(f"Action data: {action_data}")

                    # Handle SET_REMINDER and SCHEDULE_MEETING
                    if action['action_type'] == 'SET_REMINDER':
                        # Convert reminder to calendar event
                        action_data['duration_minutes'] = 30  # Default duration for reminders
                        if 'for_user' in action_data:
                            action_data['participants'] = [action_data['for_user']]
                    
                    # Schedule the event
                    success, message = self.calendar_service.schedule_event(action_data)

                    # Update status
                    status = "COMPLETED" if success else "FAILED"
                    self.supabase_service.update_calendar_action_status(
                        action['id'], 
                        status, 
                        message
                    )

                    results.append({
                        'action_id': action['id'],
                        'status': status,
                        'message': message
                    })

                except Exception as e:
                    error_msg = f"Error processing calendar action {action['id']}: {str(e)}"
                    logging.error(error_msg)
                    self.supabase_service.update_calendar_action_status(
                        action['id'],
                        "FAILED",
                        error_msg
                    )

            return results

        except Exception as e:
            logging.error(f"Error in calendar action processing: {str(e)}")
            return []