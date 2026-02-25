import pandas as pd
import database
from datetime import datetime

def import_project(file, user_id):
    """
    Parses the Project Template Excel and inserts data into the DB.
    Updated: handles 'Responsible (Username)' and 'Expected Output' columns.
    """
    # Load Excel
    xl = pd.ExcelFile(file)
    
    # 1. Parse Project Info (from Project_Schedule sheet headers)
    df_info = pd.read_excel(xl, "Project_Schedule", header=None)
    
    project_data = {
        'project_name': df_info.iloc[4, 1],    # B5
        'project_number': str(df_info.iloc[5, 1]),# B6
        'client': df_info.iloc[6, 1],          # B7
        'total_budget': float(df_info.iloc[4, 5]) if pd.notna(df_info.iloc[4, 5]) else 0.0, # F5
        'start_date': str(df_info.iloc[5, 5])[:10] if pd.notna(df_info.iloc[5, 5]) else None, # F6
        'target_end_date': str(df_info.iloc[6, 5])[:10] if pd.notna(df_info.iloc[6, 5]) else None, # F7
        'pm_user_id': user_id
    }
    
    # Create Project in DB
    project_id = database.create_project(project_data, user_id)
    
    # 2. Parse Baseline Schedule (Row 11 is Header)
    df_schedule = pd.read_excel(xl, "Project_Schedule", skiprows=10)
    # Use index-based access to be resilient to minor naming changes
    # Col 1: Activity, Col 2: Output, Col 3: Start, Col 4: End, Col 5: Budget, Col 6: Depends, Col 7: ActStart, Col 8: ActEnd, Col 9: Responsible
    
    for _, row in df_schedule.iterrows():
        # Get values by index to match the reference structure
        activity_name = row.iloc[1] if len(row) > 1 else None
        if pd.isna(activity_name): continue
        
        expected_output = row.iloc[2] if len(row) > 2 else None
        p_start = str(row.iloc[3])[:10] if len(row) > 3 and pd.notna(row.iloc[3]) else None
        p_end = str(row.iloc[4])[:10] if len(row) > 4 and pd.notna(row.iloc[4]) else None
        budget = float(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else 0.0
        depends = row.iloc[6] if len(row) > 6 and pd.notna(row.iloc[6]) and row.iloc[6] != '-' else None
        
        # Actual progress for status derivation
        act_start_val = row.iloc[7] if len(row) > 7 else None
        act_end_val = row.iloc[8] if len(row) > 8 else None
        
        # Person Responsible
        responsible_username = row.iloc[9] if len(row) > 9 else None
        responsible_user_id = None
        if pd.notna(responsible_username) and str(responsible_username).strip():
            user = database.get_user_by_username(str(responsible_username).strip())
            if user:
                responsible_user_id = user['user_id']
        
        expected_output = str(expected_output).strip() if pd.notna(expected_output) and str(expected_output).strip() else None
        
        # Derive Status
        status = 'Not Started'
        if pd.notna(act_end_val):
            status = 'Complete'
        elif pd.notna(act_start_val):
            status = 'Active'
            
        # Insert into baseline_schedule
        query = '''
        INSERT INTO baseline_schedule (project_id, activity_name, planned_start, planned_finish, budgeted_cost, depends_on, responsible_user_id, expected_output, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        activity_id = database.execute_query(query, (project_id, activity_name, p_start, p_end, budget, depends, responsible_user_id, expected_output, status), commit=True)
        
        # Seed activity log for history
        if status == 'Active':
            database.update_activity_log(activity_id, 'STARTED', str(row['Actual Start'])[:10], user_id)
        elif status == 'Complete':
            act_start = str(row['Actual Start'])[:10] if pd.notna(row.get('Actual Start')) else p_start
            database.update_activity_log(activity_id, 'STARTED', act_start, user_id)
            database.update_activity_log(activity_id, 'FINISHED', str(row['Actual End'])[:10], user_id)

    # 3. Parse Expenditure Log
    df_exp = pd.read_excel(xl, "Expenditure_Log", skiprows=3)
    df_exp = df_exp.dropna(subset=['Amount (R)'])
    
    for _, row in df_exp.iterrows():
        data = {
            'project_id': project_id,
            'activity_id': None,
            'category': row['Category'],
            'description': row['Description'],
            'reference_id': row['Reference (Invoice/PO)'],
            'amount': float(row['Amount (R)']),
            'spend_date': str(row['Date'])[:10]
        }
        database.add_expenditure(data, user_id)
        
    # 4. Parse Risk Register
    if "Risk_Register" in xl.sheet_names:
        df_risk = pd.read_excel(xl, "Risk_Register", skiprows=2)
        df_risk = df_risk.dropna(subset=['Risk/Issue Description'])
        
        for _, row in df_risk.iterrows():
            risk_data = {
                'project_id': project_id,
                'date_identified': str(row['Date Identified'])[:10] if pd.notna(row['Date Identified']) else None,
                'description': row['Risk/Issue Description'],
                'impact': str(row['Impact (H/M/L)']).upper() if pd.notna(row['Impact (H/M/L)']) else 'M',
                'status': row['Status'] if pd.notna(row['Status']) else 'Open',
                'mitigation_action': row['Mitigation Action'] if pd.notna(row['Mitigation Action']) else None
            }
            database.add_risk(risk_data, user_id)

    return project_id
