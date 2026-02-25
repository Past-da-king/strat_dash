import pandas as pd
import database
import io
import streamlit as st

import zipfile
import os

def generate_full_archive():
    """Packages the DB, Excel data, and all uploads into a single ZIP file."""
    output = io.BytesIO()
    
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add the SQLite DB File
        if hasattr(database, 'SQLITE_DB_PATH') and os.path.exists(database.SQLITE_DB_PATH):
            zip_file.write(database.SQLITE_DB_PATH, arcname='database/pm_tool.db')
            
        # 2. Add the Excel Export
        excel_data = export_all_data()
        zip_file.writestr('data_backup.xlsx', excel_data)
        
        # 3. Add all Uploaded Documents
        uploads_root = database.UPLOADS_DIR
        if os.path.exists(uploads_root):
            for root, dirs, files in os.walk(uploads_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create a relative path inside the zip to maintain structure
                    arcname = os.path.join('documents', os.relpath(file_path, uploads_root))
                    zip_file.write(file_path, arcname=arcname)
                    
    return output.getvalue()

def get_sqlite_db_file():
    """Returns the raw bytes of the SQLite database file."""
    if hasattr(database, 'SQLITE_DB_PATH') and os.path.exists(database.SQLITE_DB_PATH):
        with open(database.SQLITE_DB_PATH, 'rb') as f:
            return f.read()
    return None

def export_all_data():
    """Exports all database tables into a single multi-sheet Excel workbook."""
    tables = [
        "users", "projects", "baseline_schedule", "activity_log", 
        "expenditure_log", "project_assignments", "audit_log", "risks", "task_outputs"
    ]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for table in tables:
            df = database.get_df(f"SELECT * FROM {table}")
            if not df.empty:
                # Convert date/datetime objects to strings for Excel compatibility if needed
                for col in df.columns:
                    if df[col].dtype == 'object':
                        try:
                            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                df.to_excel(writer, sheet_name=table, index=False)
            else:
                # Even if empty, create a sheet with headers
                pd.DataFrame(columns=[table]).to_excel(writer, sheet_name=table, index=False)
                
    return output.getvalue()

def import_all_data(uploaded_file):
    """Imports data from a multi-sheet Excel workbook into the database."""
    try:
        xl = pd.ExcelFile(uploaded_file)
        # Order is important for foreign key constraints
        tables = [
            "users", "projects", "baseline_schedule", "activity_log", 
            "expenditure_log", "project_assignments", "audit_log", "risks", "task_outputs"
        ]
        
        # 1. Clear existing data (Careful!)
        # We start from the tables that have dependencies (reverse order)
        for table in reversed(tables):
            database.execute_query(f"DELETE FROM {table}", commit=True)
            
        # 2. Insert new data
        for table in tables:
            if table in xl.sheet_names:
                df = pd.read_excel(xl, sheet_name=table)
                if not df.empty:
                    # Clean the dataframe (replace NaN with None for SQL)
                    df = df.where(pd.notnull(df), None)
                    
                    columns = ", ".join(df.columns)
                    placeholders = ", ".join(["%s"] * len(df.columns))
                    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    
                    for _, row in df.iterrows():
                        database.execute_query(query, tuple(row), commit=True)
        return True, "Data imported successfully!"
    except Exception as e:
        return False, f"Import failed: {str(e)}"
