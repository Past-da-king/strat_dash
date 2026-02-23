"""
PM Tool - System Initializer
Run this file once to set up your environment and database.
"""
import os
import subprocess
import sys

def setup():
    print("=" * 60)
    print("🚀 PM TOOL SYSTEM SETUP")
    print("=" * 60)

    # 1. Check dependencies
    print("\n📦 Step 1: Checking Dependencies...")
    try:
        import streamlit
        import pandas
        import plotly
        import openpyxl
        import werkzeug
        print("  ✅ All libraries found.")
    except ImportError as e:
        print(f"  ❌ Missing library: {e}")
        print("  Please run: pip install streamlit pandas plotly openpyxl werkzeug")
        return

    # 2. Initialize Database
    print("\n🗄️ Step 2: Initializing Database...")
    try:
        from pmt_app import init_db
        init_db.init_db()
        print("  ✅ Database created and seeded with test users.")
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return

    # 3. Create Excel Templates
    print("\n📊 Step 3: Generating Project Templates...")
    try:
        import generate_template
        generate_template.create_professional_template(sample_data=False)
        generate_template.create_professional_template(sample_data=True)
        print("  ✅ Project_Template.xlsx created.")
    except Exception as e:
        print(f"  ⚠️ Template warning: {e} (File might be open in Excel)")

    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("\nTo start the application, run:")
    print("streamlit run pmt_app/main.py")
    print("\nLogin Credentials (Admin):")
    print("Username: admin")
    print("Password: admin123")
    print("=" * 60)

if __name__ == "__main__":
    setup()
