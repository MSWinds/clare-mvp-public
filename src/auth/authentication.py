"""
Authentication and Profile Management Module
Handles sign-in logic, profile retrieval, and questionnaire processing.
"""

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
import json
from typing import Optional, Dict, Any

# Import database config
from src.database.config import get_database_engine, student_profiles_table, chat_history_table

def get_profile_by_student_id(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve profile for a specific student ID from the database.
    Returns the most recent profile if found, None otherwise.
    """
    if not student_id.strip():
        return None

    try:
        engine = get_database_engine()
        query = text("""
            SELECT profile_summary, timestamp
            FROM student_profiles
            WHERE student_id = :student_id
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"student_id": student_id.strip()}).fetchone()

            if result:
                profile_summary = result[0]
                timestamp = result[1]

                # Handle both JSONB and text formats
                if isinstance(profile_summary, dict):
                    return profile_summary
                elif isinstance(profile_summary, str):
                    try:
                        return json.loads(profile_summary)
                    except json.JSONDecodeError:
                        # If it's a plain text summary, wrap it
                        return {"text_summary": profile_summary, "timestamp": timestamp.isoformat()}

            return None

    except Exception as e:
        print(f"Error retrieving profile for {student_id}: {e}")
        return None

def initialize_session_state():
    """Initialize all session state variables for authentication."""
    if "profile_data" not in st.session_state:
        st.session_state["profile_data"] = None
    if "student_id" not in st.session_state:
        st.session_state["student_id"] = ""
    if "show_profile_form" not in st.session_state:
        st.session_state["show_profile_form"] = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def handle_sign_in():
    """Handle sign-in button click - triggers the profile form."""
    st.session_state["show_profile_form"] = True
    st.rerun()

def handle_profile_edit():
    """Handle profile edit button click - triggers the profile form."""
    st.session_state["show_profile_form"] = True
    st.rerun()

def handle_profile_cancel():
    """Handle profile form cancel."""
    st.session_state["show_profile_form"] = False
    st.rerun()

def store_chat_to_db(student_id: str, user_input: str, ai_response: str):
    """Store chat interaction to database."""
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            insert_stmt = chat_history_table.insert().values(
                id=uuid.uuid4(),
                student_id=student_id,
                user_input=user_input,
                ai_response=ai_response,
                timestamp=datetime.now(timezone.utc)
            )
            conn.execute(insert_stmt)
            conn.commit()
            print(f"Inserted chat for {student_id} at {datetime.now(timezone.utc)}")

        # Trigger profile update check after storing chat
        if should_trigger_profile_update(student_id):
            trigger_profile_update(student_id)

    except SQLAlchemyError as e:
        print(f"Failed to insert chat into DB: {e}")

def should_trigger_profile_update(student_id: str) -> bool:
    """
    Determine if a profile update should be triggered based on interaction patterns.
    Smart triggering to avoid updates for trivial exchanges.
    """
    try:
        engine = get_database_engine()
        with engine.connect() as conn:
            # Check interaction count since last profile update
            query = text("""
                WITH last_profile_update AS (
                    SELECT COALESCE(MAX(timestamp), '1970-01-01'::timestamp) as last_update
                    FROM student_profiles
                    WHERE student_id = :student_id
                ),
                recent_interactions AS (
                    SELECT COUNT(*) as interaction_count
                    FROM chat_history
                    WHERE student_id = :student_id
                    AND timestamp > (SELECT last_update FROM last_profile_update)
                )
                SELECT interaction_count FROM recent_interactions;
            """)

            result = conn.execute(query, {"student_id": student_id}).fetchone()
            interaction_count = result[0] if result else 0

            # Trigger update every 5 interactions
            return interaction_count > 0 and interaction_count % 5 == 0

    except Exception as e:
        print(f"Error checking profile update trigger for {student_id}: {e}")
        return False

def trigger_profile_update(student_id: str):
    """Trigger background profile update."""
    try:
        # Import here to avoid circular imports
        from src.workflows.profile_analyzer import run_profile_analysis

        # Run profile analysis in background
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, schedule the coroutine
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(run_profile_analysis(student_id, "interaction"))
                    )
                    print(f"🔄 Profile update scheduled for {student_id}")
            else:
                # We can run the coroutine directly
                asyncio.run(run_profile_analysis(student_id, "interaction"))
                print(f"✅ Profile update completed for {student_id}")
        except Exception as e:
            print(f"Profile update failed for {student_id}: {e}")

    except Exception as e:
        print(f"Failed to trigger profile update for {student_id}: {e}")

def is_user_signed_in() -> bool:
    """Check if user is currently signed in."""
    return st.session_state.get("profile_data") is not None

def get_current_student_name() -> str:
    """Get the current student's name, or 'Student' as default."""
    if is_user_signed_in():
        return st.session_state["profile_data"].get("name", "Student")
    return "Student"

def get_current_student_id() -> str:
    """Get the current student's ID."""
    return st.session_state.get("student_id", "")