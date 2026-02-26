import pandas as pd
import database
import io
import streamlit as st

import zipfile
import os

def generate_full_archive():
    """Packages the DB, Excel data, and all Azure uploads into a single ZIP file."""
    from azure.storage.blob import BlobServiceClient
    output = io.BytesIO()
    
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Add the SQLite DB File
        if hasattr(database, 'SQLITE_DB_PATH') and os.path.exists(database.SQLITE_DB_PATH):
            zip_file.write(database.SQLITE_DB_PATH, arcname='database/pm_tool.db')
            
        # 2. Add the Excel Export
        excel_data = export_all_data()
        zip_file.writestr('data_backup.xlsx', excel_data)
        
        # 3. Add all uploaded documents from Azure Blob Storage
        try:
            blob_service = BlobServiceClient.from_connection_string(database.AZURE_CONNECTION)
            container = blob_service.get_container_client(database.AZURE_CONTAINER)
            for blob in container.list_blobs(name_starts_with="uploads/"):
                blob_data = container.get_blob_client(blob.name).download_blob().readall()
                # store in zip as documents/<rest of path after 'uploads/'>
                arcname = "documents/" + blob.name[len("uploads/"):]
                zip_file.writestr(arcname, blob_data)
        except Exception as e:
            st.warning(f"Could not archive cloud documents: {e}")
                    
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

import shutil

def import_from_db(uploaded_file):
    """Replaces the current SQLite database with the uploaded .db file."""
    try:
        # Close connection to current DB first if possible (though SQLite handles this ok)
        with open(database.SQLITE_DB_PATH, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        st.cache_data.clear()
        return True, "Database restored successfully from .db file!"
    except Exception as e:
        return False, f"DB Restoration failed: {str(e)}"

def import_from_zip(uploaded_file):
    """Restores the entire system (DB + Documents) from a ZIP archive."""
    try:
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            # 1. Restore Database
            if 'database/pm_tool.db' in zip_ref.namelist():
                db_data = zip_ref.read('database/pm_tool.db')
                with open(database.SQLITE_DB_PATH, 'wb') as f:
                    f.write(db_data)

            # 2. Restore Documents
            # Extract only files starting with 'documents/' to the uploads folder
            for member in zip_ref.namelist():
                if member.startswith('documents/'):
                    # Strip the 'documents/' prefix to put them back in 'uploads/'
                    filename = member.replace('documents/', '', 1)
                    if filename: # Avoid directory members
                        # Ensure forward slashes for Azure Blob Storage
                        blob_name = f"uploads/{filename}".replace('\\', '/')
                        # Upload byte content directly to Azure (skip validation for backup restoration)
                        database.upload_file_to_azure(zip_ref.read(member), blob_name, validate=False)

        st.cache_data.clear()
        return True, "System fully restored from ZIP archive (DB and Documents)!"
    except Exception as e:
        return False, f"ZIP Restoration failed: {str(e)}"

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
