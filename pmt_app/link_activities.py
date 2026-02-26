import os
import sys

# Ensure we can import the database module from the pmt_app directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import database
except ImportError:
    print("Error: Could not find database.py. Ensure this script is in the pmt_app directory.")
    sys.exit(1)

def run_linking_automation(project_id):
    """
    Demonstrates reading activities and updating dependencies in the database.
    This example links activities in a linear sequence based on their start dates.
    """
    print(f"--- Database Access: Reading activities for Project {project_id} ---")
    
    # 1. READ: Fetch all activities for the project
    # We order by planned_start to establish a logical sequence
    activities = database.execute_query(
        "SELECT activity_id, activity_name, planned_start FROM baseline_schedule WHERE project_id = %s ORDER BY planned_start ASC",
        (project_id,)
    )
    
    if not activities:
        print(f"No activities found for project ID {project_id}. Check your database.")
        return

    print(f"Found {len(activities)} activities.")
    print("--- Linking activities by dependencies ---")

    # 2. LINK & UPDATE:
    # We iterate through the list and make each activity (i) depend on the one before it (i-1)
    for i in range(1, len(activities)):
        current_activity = activities[i]
        previous_activity = activities[i-1]
        
        current_id = current_activity['activity_id']
        parent_id = previous_activity['activity_id']
        
        # 3. UPDATE: Save the dependency link back to the database
        database.execute_query(
            "UPDATE baseline_schedule SET depends_on = %s WHERE activity_id = %s",
            (parent_id, current_id),
            commit=True
        )
        
        print(f"SUCCESS: '{current_activity['activity_name']}' (ID: {current_id}) now depends on '{previous_activity['activity_name']}' (ID: {parent_id})")

    print("
Database update complete. You can now view the Critical Path in the Network Diagram.")

if __name__ == "__main__":
    # You can change this ID to target a specific project in your pm_tool.db
    PROJECT_ID_TO_LINK = 1 
    
    # Check if DB exists
    if os.path.exists(database.SQLITE_DB_PATH):
        run_linking_automation(PROJECT_ID_TO_LINK)
    else:
        print(f"Database not found at {database.SQLITE_DB_PATH}")
