import sqlite3
import os

DB_PATH = 'pmt_app/pm_tool.db'

def get_schema(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    conn.close()
    return columns

tables = ['users', 'baseline_schedule', 'project_assignments']
for table in tables:
    print(f"\nSchema for {table}:")
    for col in get_schema(table):
        print(col)
