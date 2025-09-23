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
            SELECT profile_summary, timestamp, student_name
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
                student_name = result[2]

                # Handle both JSONB and text formats
                if isinstance(profile_summary, dict):
                    # Add student_name to the profile data
                    profile_data = profile_summary.copy()
                    if student_name:
                        profile_data["name"] = student_name
                    return profile_data
                elif isinstance(profile_summary, str):
                    try:
                        profile_data = json.loads(profile_summary)
                        if student_name:
                            profile_data["name"] = student_name
                        return profile_data
                    except json.JSONDecodeError:
                        # If it's a plain text summary, wrap it
                        profile_data = {"text_summary": profile_summary, "timestamp": timestamp.isoformat()}
                        if student_name:
                            profile_data["name"] = student_name
                        return profile_data

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
    if "show_signin_form" not in st.session_state:
        st.session_state["show_signin_form"] = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "user_status" not in st.session_state:
        st.session_state["user_status"] = None

def handle_sign_in():
    """Handle sign-in button click - triggers the sign-in form."""
    st.session_state["show_signin_form"] = True
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
    """Store chat interaction to database. Coerces non-string responses to JSON strings."""
    try:
        engine = get_database_engine()
        # Normalize inputs to strings for TEXT columns
        try:
            ui_text = user_input if isinstance(user_input, str) else str(user_input)
        except Exception:
            ui_text = str(user_input)

        try:
            if isinstance(ai_response, (dict, list)):
                ai_text = json.dumps(ai_response, ensure_ascii=False)
            else:
                ai_text = ai_response if isinstance(ai_response, str) else str(ai_response)
        except Exception:
            ai_text = str(ai_response)
        with engine.connect() as conn:
            insert_stmt = chat_history_table.insert().values(
                id=uuid.uuid4(),
                student_id=student_id,
                user_input=ui_text,
                ai_response=ai_text,
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
        from src.workflows.profile_analyzer import analyze_and_update_profile

        # Run profile analysis in background
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an event loop, schedule the coroutine
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(analyze_and_update_profile(student_id, "interaction"))
                    )
                    print(f"🔄 Profile update scheduled for {student_id}")
            else:
                # We can run the coroutine directly
                asyncio.run(analyze_and_update_profile(student_id, "interaction"))
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
        # First try to get from session state
        name = st.session_state["profile_data"].get("name")
        if name:
            return name

        # If not in session state, try to get from database
        student_id = get_current_student_id()
        if student_id:
            try:
                engine = get_database_engine()
                query = text("""
                    SELECT student_name
                    FROM student_profiles
                    WHERE student_id = :student_id
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)

                with engine.connect() as conn:
                    result = conn.execute(query, {"student_id": student_id}).fetchone()
                    if result and result[0]:
                        return result[0]
            except Exception as e:
                print(f"Error retrieving student name from database: {e}")

    return "Student"

def get_current_student_id() -> str:
    """Get the current student's ID."""
    return st.session_state.get("student_id", "")

def show_signin_form():
    """Display the simple sign-in form for Student ID entry."""
    st.markdown("### 🔑 Sign In to Clare-AI")
    st.markdown("Enter your Student ID to continue")

    with st.form("signin_form"):
        student_id = st.text_input(
            "Student ID",
            placeholder="Enter your student ID (e.g., john.doe@cgu.edu)",
            help="Use your CGU email or any unique identifier"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button("🚀 Continue", type="primary", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit_button:
            if not student_id.strip():
                st.error("⚠️ Please enter your Student ID")
            else:
                # Store student ID and check user status
                st.session_state["student_id"] = student_id.strip()
                user_status = check_user_status(student_id.strip())
                st.session_state["user_status"] = user_status

                # Close sign-in form
                st.session_state["show_signin_form"] = False

                if user_status["is_new_user"] or not user_status["is_profile_complete"]:
                    # New user - show questionnaire
                    st.session_state["show_profile_form"] = True
                    st.success(f"👋 Welcome! Let's set up your profile.")
                else:
                    # Returning user - set profile data and update login
                    existing_profile = get_profile_by_student_id(student_id.strip())
                    if existing_profile:
                        st.session_state["profile_data"] = existing_profile
                    update_last_login(student_id.strip())
                    st.success(f"🎉 Welcome back! You're ready to chat with Clare-AI.")

                st.rerun()

        elif cancel_button:
            st.session_state["show_signin_form"] = False
            st.rerun()

def check_user_status(student_id: str) -> Dict[str, Any]:
    """
    Check if user is new or returning and their profile completion status.

    Returns:
        dict with keys: is_new_user, is_profile_complete, last_login, profile_version
    """
    if not student_id.strip():
        return {
            "is_new_user": True,
            "is_profile_complete": False,
            "last_login": None,
            "profile_version": 0
        }

    try:
        engine = get_database_engine()
        query = text("""
            SELECT is_profile_complete, last_login, profile_version
            FROM student_profiles
            WHERE student_id = :student_id
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"student_id": student_id.strip()}).fetchone()

            if result:
                # Returning user
                return {
                    "is_new_user": False,
                    "is_profile_complete": result[0],
                    "last_login": result[1],
                    "profile_version": result[2]
                }
            else:
                # New user
                return {
                    "is_new_user": True,
                    "is_profile_complete": False,
                    "last_login": None,
                    "profile_version": 0
                }

    except Exception as e:
        print(f"Error checking user status for {student_id}: {e}")
        # Default to new user on error
        return {
            "is_new_user": True,
            "is_profile_complete": False,
            "last_login": None,
            "profile_version": 0
        }

def update_last_login(student_id: str):
    """Update the last_login timestamp for a user."""
    try:
        engine = get_database_engine()
        query = text("""
            UPDATE student_profiles
            SET last_login = :current_time
            WHERE student_id = :student_id
        """)

        with engine.connect() as conn:
            conn.execute(query, {
                "student_id": student_id.strip(),
                "current_time": datetime.now(timezone.utc)
            })
            conn.commit()
            print(f"Updated last_login for {student_id}")

    except Exception as e:
        print(f"Error updating last_login for {student_id}: {e}")

