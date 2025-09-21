"""
Test all imports to identify issues before running main.py
"""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module and report results"""
    try:
        exec(f"import {module_name}")
        print(f"✅ {description}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {description}: FAILED")
        print(f"   Error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_from_import(import_statement, description):
    """Test a from-import statement"""
    try:
        exec(import_statement)
        print(f"✅ {description}: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ {description}: FAILED")
        print(f"   Error: {e}")
        print(f"   Import: {import_statement}")
        return False

print("🧪 Testing all imports for Clare-AI...")
print("=" * 50)

# Basic imports
test_import("streamlit", "Streamlit")
test_import("asyncio", "Asyncio")
test_import("traceback", "Traceback")

# Environment and database
test_from_import("from dotenv import load_dotenv", "Environment variables")
test_from_import("from sqlalchemy import create_engine", "SQLAlchemy")

# Our modules
print("\n🔧 Testing our custom modules...")
test_from_import("from src.database.config import validate_env_vars", "Database config")
test_from_import("from src.auth.authentication import initialize_session_state", "Authentication")
test_from_import("from src.prompts.system_prompts import query_router_prompt_template", "Prompts")
test_from_import("from src.auth.profile_form import show_profile_form", "Profile form")

# Workflow imports (these might fail due to complex dependencies)
print("\n⚙️  Testing workflow modules...")
test_from_import("from src.workflows.agentic_workflow import get_workflow", "Agentic workflow")

# LangChain and LangSmith
print("\n🔗 Testing LangChain/LangSmith...")
test_from_import("from langsmith import Client", "LangSmith Client")
test_from_import("from streamlit_feedback import streamlit_feedback", "Streamlit Feedback")
test_from_import("from langchain_core.tracers.context import collect_runs", "LangChain tracers")

print("\n" + "=" * 50)
print("🎯 Import testing complete!")
print("Run this script to see which imports are failing.")