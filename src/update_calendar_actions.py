import logging
from supabase_service import SupabaseService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def update_existing_calendar_actions():
    """Update existing calendar actions with properly parsed action data"""
    supabase_service = SupabaseService()
    
    try:
        # Fetch all pending calendar actions
        actions = supabase_service.fetch_calendar_actions()
        if not actions:
            logging.info("No pending calendar actions found")
            return

        logging.info(f"Found {len(actions)} pending calendar actions to update")

        for action in actions:
            try:
                # Extract action data from insights
                insights = action.get('insights', '')
                action_data = supabase_service.extract_action_data(insights)

                if action_data:
                    # Update the record with parsed action_data
                    response = supabase_service.supabase.table('analysis')\
                        .update({'action_data': action_data})\
                        .eq('id', action['id'])\
                        .execute()
                    
                    if response.data:
                        logging.info(f"Updated action_data for action {action['id']}")
                        logging.info(f"Action data: {action_data}")
                    else:
                        logging.error(f"Failed to update action_data for action {action['id']}")
                else:
                    logging.warning(f"Could not extract action data from insights for action {action['id']}")

            except Exception as e:
                logging.error(f"Error processing action {action['id']}: {str(e)}")

    except Exception as e:
        logging.error(f"Error updating calendar actions: {str(e)}")

if __name__ == "__main__":
    update_existing_calendar_actions()