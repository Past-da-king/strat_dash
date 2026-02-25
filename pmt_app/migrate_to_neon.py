"""
One-time migration script: SQLite → Neon PostgreSQL
Copies all existing data from the local pm_tool.db into the remote Neon database.
"""
import sqlite3
import psycopg2
import os
import sys

# Add the pmt_app directory to the path so we can import streamlit secrets
sys.path.insert(0, os.path.dirname(__file__))

SQLITE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pm_tool.db')

# Read Neon URL from secrets.toml manually (don't need Streamlit runtime)
import tomllib
SECRETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.streamlit', 'secrets.toml')
with open(SECRETS_PATH, 'rb') as f:
    secrets = tomllib.load(f)
NEON_URL = secrets['database']['url']

def migrate():
    if not os.path.exists(SQLITE_DB):
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    # Connect to both databases
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = psycopg2.connect(NEON_URL)
    pg_cur = pg_conn.cursor()

    try:
        # ============================================================
        # 1. MIGRATE USERS (skip if already seeded with same username)
        # ============================================================
        print("\n--- Migrating USERS ---")
        sqlite_cur.execute("SELECT * FROM users")
        users = sqlite_cur.fetchall()
        for row in users:
            pg_cur.execute("SELECT 1 FROM users WHERE username = %s", (row['username'],))
            if pg_cur.fetchone():
                print(f"  SKIP (exists): {row['username']}")
                continue
            pg_cur.execute("""
                INSERT INTO users (user_id, username, password_hash, role, full_name, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (row['user_id'], row['username'], row['password_hash'], row['role'], row['full_name'], row['status']))
            print(f"  MIGRATED: {row['username']} (role: {row['role']})")

        # Reset the users sequence to avoid ID conflicts on future inserts
        pg_cur.execute("SELECT MAX(user_id) FROM users")
        max_uid = pg_cur.fetchone()[0] or 0
        pg_cur.execute(f"SELECT setval('users_user_id_seq', {max_uid})")
        pg_conn.commit()

        # ============================================================
        # 2. MIGRATE PROJECTS
        # ============================================================
        print("\n--- Migrating PROJECTS ---")
        sqlite_cur.execute("SELECT * FROM projects")
        projects = sqlite_cur.fetchall()
        for row in projects:
            pg_cur.execute("SELECT 1 FROM projects WHERE project_number = %s", (row['project_number'],))
            if pg_cur.fetchone():
                print(f"  SKIP (exists): {row['project_name']}")
                continue
            pg_cur.execute("""
                INSERT INTO projects (project_id, project_name, project_number, client, pm_user_id, total_budget, start_date, target_end_date, status, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (row['project_id'], row['project_name'], row['project_number'], row['client'],
                  row['pm_user_id'], row['total_budget'], row['start_date'], row['target_end_date'],
                  row['status'], row['created_by']))
            print(f"  MIGRATED: {row['project_name']} ({row['project_number']})")

        pg_cur.execute("SELECT MAX(project_id) FROM projects")
        max_pid = pg_cur.fetchone()[0] or 0
        pg_cur.execute(f"SELECT setval('projects_project_id_seq', {max_pid})")
        pg_conn.commit()

        # ============================================================
        # 3. MIGRATE BASELINE SCHEDULE
        # ============================================================
        print("\n--- Migrating BASELINE SCHEDULE ---")
        sqlite_cur.execute("SELECT * FROM baseline_schedule")
        activities = sqlite_cur.fetchall()
        for row in activities:
            pg_cur.execute("SELECT 1 FROM baseline_schedule WHERE activity_id = %s", (row['activity_id'],))
            if pg_cur.fetchone():
                print(f"  SKIP (exists): {row['activity_name']}")
                continue
            pg_cur.execute("""
                INSERT INTO baseline_schedule (activity_id, project_id, activity_name, planned_start, planned_finish, budgeted_cost, depends_on, responsible_user_id, expected_output, status, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (row['activity_id'], row['project_id'], row['activity_name'], row['planned_start'],
                  row['planned_finish'], row['budgeted_cost'], row['depends_on'], row['responsible_user_id'],
                  row['expected_output'], row['status'], row['sort_order']))
            print(f"  MIGRATED: {row['activity_name']}")

        pg_cur.execute("SELECT MAX(activity_id) FROM baseline_schedule")
        max_aid = pg_cur.fetchone()[0] or 0
        pg_cur.execute(f"SELECT setval('baseline_schedule_activity_id_seq', {max_aid})")
        pg_conn.commit()

        # ============================================================
        # 4. MIGRATE ACTIVITY LOG
        # ============================================================
        print("\n--- Migrating ACTIVITY LOG ---")
        sqlite_cur.execute("SELECT * FROM activity_log")
        logs = sqlite_cur.fetchall()
        for row in logs:
            pg_cur.execute("SELECT 1 FROM activity_log WHERE log_id = %s", (row['log_id'],))
            if pg_cur.fetchone():
                continue
            pg_cur.execute("""
                INSERT INTO activity_log (log_id, activity_id, event_type, event_date, recorded_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['log_id'], row['activity_id'], row['event_type'], row['event_date'], row['recorded_by']))
        print(f"  MIGRATED: {len(logs)} log entries")

        if logs:
            pg_cur.execute("SELECT MAX(log_id) FROM activity_log")
            max_lid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('activity_log_log_id_seq', {max_lid})")
        pg_conn.commit()

        # ============================================================
        # 5. MIGRATE EXPENDITURE LOG
        # ============================================================
        print("\n--- Migrating EXPENDITURE LOG ---")
        sqlite_cur.execute("SELECT * FROM expenditure_log")
        exps = sqlite_cur.fetchall()
        for row in exps:
            pg_cur.execute("SELECT 1 FROM expenditure_log WHERE exp_id = %s", (row['exp_id'],))
            if pg_cur.fetchone():
                continue
            pg_cur.execute("""
                INSERT INTO expenditure_log (exp_id, project_id, activity_id, category, description, reference_id, amount, spend_date, recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (row['exp_id'], row['project_id'], row['activity_id'], row['category'],
                  row['description'], row['reference_id'], row['amount'], row['spend_date'], row['recorded_by']))
        print(f"  MIGRATED: {len(exps)} expenditure entries")

        if exps:
            pg_cur.execute("SELECT MAX(exp_id) FROM expenditure_log")
            max_eid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('expenditure_log_exp_id_seq', {max_eid})")
        pg_conn.commit()

        # ============================================================
        # 6. MIGRATE PROJECT ASSIGNMENTS
        # ============================================================
        print("\n--- Migrating PROJECT ASSIGNMENTS ---")
        sqlite_cur.execute("SELECT * FROM project_assignments")
        assignments = sqlite_cur.fetchall()
        for row in assignments:
            pg_cur.execute("SELECT 1 FROM project_assignments WHERE project_id = %s AND user_id = %s", (row['project_id'], row['user_id']))
            if pg_cur.fetchone():
                print(f"  SKIP (exists): project {row['project_id']} <-> user {row['user_id']}")
                continue
            pg_cur.execute("""
                INSERT INTO project_assignments (assignment_id, project_id, user_id, assigned_role, assigned_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['assignment_id'], row['project_id'], row['user_id'], row['assigned_role'], row['assigned_by']))
        print(f"  MIGRATED: {len(assignments)} assignments")

        if assignments:
            pg_cur.execute("SELECT MAX(assignment_id) FROM project_assignments")
            max_asid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('project_assignments_assignment_id_seq', {max_asid})")
        pg_conn.commit()

        # ============================================================
        # 7. MIGRATE AUDIT LOG
        # ============================================================
        print("\n--- Migrating AUDIT LOG ---")
        sqlite_cur.execute("SELECT * FROM audit_log")
        audits = sqlite_cur.fetchall()
        for row in audits:
            pg_cur.execute("SELECT 1 FROM audit_log WHERE audit_id = %s", (row['audit_id'],))
            if pg_cur.fetchone():
                continue
            pg_cur.execute("""
                INSERT INTO audit_log (audit_id, table_name, record_id, action, old_value, new_value, changed_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (row['audit_id'], row['table_name'], row['record_id'], row['action'],
                  row['old_value'], row['new_value'], row['changed_by']))
        print(f"  MIGRATED: {len(audits)} audit entries")

        if audits:
            pg_cur.execute("SELECT MAX(audit_id) FROM audit_log")
            max_auid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('audit_log_audit_id_seq', {max_auid})")
        pg_conn.commit()

        # ============================================================
        # 8. MIGRATE RISKS
        # ============================================================
        print("\n--- Migrating RISKS ---")
        sqlite_cur.execute("SELECT * FROM risks")
        risks = sqlite_cur.fetchall()
        for row in risks:
            pg_cur.execute("SELECT 1 FROM risks WHERE risk_id = %s", (row['risk_id'],))
            if pg_cur.fetchone():
                continue
            pg_cur.execute("""
                INSERT INTO risks (risk_id, project_id, date_identified, description, impact, status, mitigation_action, recorded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (row['risk_id'], row['project_id'], row['date_identified'], row['description'],
                  row['impact'], row['status'], row['mitigation_action'], row['recorded_by']))
        print(f"  MIGRATED: {len(risks)} risk entries")

        if risks:
            pg_cur.execute("SELECT MAX(risk_id) FROM risks")
            max_rid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('risks_risk_id_seq', {max_rid})")
        pg_conn.commit()

        # ============================================================
        # 9. MIGRATE TASK OUTPUTS
        # ============================================================
        print("\n--- Migrating TASK OUTPUTS ---")
        sqlite_cur.execute("SELECT * FROM task_outputs")
        outputs = sqlite_cur.fetchall()
        for row in outputs:
            pg_cur.execute("SELECT 1 FROM task_outputs WHERE output_id = %s", (row['output_id'],))
            if pg_cur.fetchone():
                continue
            pg_cur.execute("""
                INSERT INTO task_outputs (output_id, activity_id, file_name, file_path, uploaded_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (row['output_id'], row['activity_id'], row['file_name'], row['file_path'], row['uploaded_by']))
        print(f"  MIGRATED: {len(outputs)} task output entries")

        if outputs:
            pg_cur.execute("SELECT MAX(output_id) FROM task_outputs")
            max_oid = pg_cur.fetchone()[0] or 0
            pg_cur.execute(f"SELECT setval('task_outputs_output_id_seq', {max_oid})")
        pg_conn.commit()

        print("\n========================================")
        print("✅ MIGRATION COMPLETE!")
        print("========================================")

    except Exception as e:
        pg_conn.rollback()
        print(f"\n❌ MIGRATION FAILED: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == '__main__':
    migrate()
