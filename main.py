"""
Clare-AI - Teaching Assistant for Generative AI Course
Simplified Streamlit Interface using Modular Architecture
"""

import streamlit as st
import asyncio
import traceback
import sys
import os
from functools import partial

# Add current directory to Python path for Streamlit Cloud compatibility
if os.path.dirname(__file__) not in sys.path:
    sys.path.append(os.path.dirname(__file__))

# Import our modular components
from src.database.config import validate_env_vars, create_tables
from src.auth.authentication import (
    initialize_session_state,
    handle_sign_in,
    handle_profile_edit,
    is_user_signed_in,
    get_current_student_name,
    get_current_student_id,
    store_chat_to_db,
    check_user_status,
    update_last_login,
    show_signin_form
)

# Import feedback functionality
from langsmith import Client
from streamlit_feedback import streamlit_feedback
from langchain_core.tracers.context import collect_runs

# Page Configuration
st.set_page_config(
    page_title='Clare-AI - TA Assistant',
    page_icon="clare_pic.jpg",
    layout="wide"
)

# Validate environment variables and initialize database
try:
    validate_env_vars()
    create_tables()
except ValueError as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# Initialize session state
initialize_session_state()

# LangSmith Client for feedback (lazy initialization)
@st.cache_resource
def get_langsmith_client():
    """Initialize LangSmith client for feedback collection."""
    try:
        return Client()
    except Exception as e:
        st.warning(f"Could not initialize LangSmith client. Feedback submission may not work. Error: {e}")
        return None

# Main App Title
st.markdown(
    """
    <h1 style='text-align: center; color: #4B8BBE;'>
        <span style='color:#306998;'>Clare-AI</span> - TA Assistant
    </h1>
    """,
    unsafe_allow_html=True
)

# Sidebar for Profile Management (condensed with expanders and reset)
with st.sidebar:
    st.image("clare_pic-removebg.png", width=200)
    st.markdown("## 🤖 Clare-AI Assistant")

    # Primary actions
    col_a, col_b = st.columns(2)
    with col_a:
        if not is_user_signed_in():
            if st.button("🔑 Sign In", use_container_width=True, type="primary"):
                handle_sign_in()
        else:
            if st.button("✏️ Profile", use_container_width=True):
                handle_profile_edit()
    with col_b:
        if st.button("🔄 New Chat", use_container_width=True):
            # Clear chat and any feedback-related keys
            st.session_state.chat_history = []
            keys_to_delete = [k for k in list(st.session_state.keys()) if str(k).startswith("feedback_")]
            for k in keys_to_delete:
                del st.session_state[k]
            st.experimental_rerun()  # Refresh UI

    # Signed-in summary with user status
    if is_user_signed_in():
        student_name = get_current_student_name()
        student_id = get_current_student_id()
        st.markdown(f"**Hello, {student_name}!**")
        st.caption(f"ID: {student_id}")

        # Show user status information
        user_status = check_user_status(student_id)
        if user_status["is_new_user"] or not user_status["is_profile_complete"]:
            st.warning("⚠️ Profile incomplete")
        else:
            st.success("✅ Profile complete")
            if user_status["last_login"]:
                last_login = user_status["last_login"].strftime("%m/%d/%Y")
                st.caption(f"Last login: {last_login}")
    else:
        st.caption("Please sign in to start using Clare-AI")

    # Compact info using expanders
    with st.expander("📚 Course Info", expanded=False):
        st.markdown("**IST 345.1 – Building Generative AI Applications**")
        st.markdown("""
        - Instructor: Yan Li – [Yan.Li@cgu.edu](mailto:Yan.Li@cgu.edu)
        - TA (Lab): Kaijie Yu – [Kaijie.Yu@cgu.edu](mailto:Kaijie.Yu@cgu.edu)
        - TA (Data): Yongjia Sun – [Yongjia.Sun@cgu.edu](mailto:Yongjia.Sun@cgu.edu)
        """)

    with st.expander("🎯 How Clare Helps", expanded=False):
        st.markdown("""
        - Socratic guidance, not direct answers
        - Personalized to your profile
        - Syllabus and materials shortcuts
        - Smart search across course docs
        """)

    # Welcome and onboarding moved from center to sidebar
    with st.expander("👋 Welcome & Getting Started", expanded=not is_user_signed_in()):
        st.markdown("""
        Clare-AI is your intelligent teaching assistant for the **Generative AI Applications** course.

        **Features**
        - 🎓 Personalized Learning: Tailored responses based on your profile
        - 📚 Course Materials: Access to lectures, readings, and assignments
        - 🤔 Socratic Method: Guided thinking instead of direct answers
        - 🔍 Smart Search: Find relevant information quickly

        **Getting Started**
        1. Click "Sign In" above
        2. Complete your learning profile (if new user)
        3. Start asking questions about the course!
        """)

# Sign-In Form (Student ID Entry)
if st.session_state.get("show_signin_form", False):
    show_signin_form()
    st.stop()

# Profile Form (for new users or profile updates)
if st.session_state.get("show_profile_form", False):
    from src.auth.profile_form import show_profile_form  # Import when needed

    # Check if this is an update or new profile
    user_status = st.session_state.get("user_status", {})
    is_update = not (user_status.get("is_new_user", True) or not user_status.get("is_profile_complete", False))

    if is_update:
        # Returning user updating profile
        st.info("✏️ Update your profile information below")
        show_profile_form(is_update=True)
    else:
        # New user completing profile for first time
        st.info("👋 Welcome! Please complete your learning profile to get started.")
        show_profile_form(is_update=False)

    st.stop()

# Main Chat Interface
if not is_user_signed_in():
    st.info("🔑 Please sign in from the sidebar to start using Clare-AI")
    st.stop()

# Chat Interface
st.markdown("### 💬 Chat with Clare-AI")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask Clare-AI about the course..."):
    # Update last login for returning users on first interaction
    student_id = get_current_student_id()
    if len(st.session_state.chat_history) == 0:  # First message in this session
        update_last_login(student_id)

    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate AI response
    with st.chat_message("assistant"):
        with st.spinner("Clare is thinking..."):
            try:
                # Import workflow when needed to avoid circular imports
                from src.workflows.agentic_workflow import get_workflow

                # Get the workflow
                workflow = get_workflow()

                # Prepare input
                student_id = get_current_student_id()
                inputs = {
                    "question": prompt,
                    "student_id": student_id
                }

                # Collect runs for feedback
                with collect_runs() as cb:
                    # Run workflow asynchronously
                    response = asyncio.run(workflow.ainvoke(inputs))

                    # Extract the final answer
                    final_answer = response.get("generation", "I'm sorry, I couldn't generate a response.")

                    # Display response
                    st.markdown(final_answer)

                    # Store chat in database
                    store_chat_to_db(student_id, prompt, final_answer)

                    # Add to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": final_answer})

                    # Feedback section
                    client = get_langsmith_client()
                    if client and cb.traced_runs:
                        run_id = cb.traced_runs[0].id
                        feedback = streamlit_feedback(
                            feedback_type="thumbs",
                            optional_text_label="Please provide additional feedback",
                            key=f"feedback_{len(st.session_state.chat_history)}"
                        )

                        if feedback:
                            # Submit feedback to LangSmith
                            try:
                                client.create_feedback(
                                    run_id=run_id,
                                    key="user_feedback",
                                    score=1 if feedback["score"] == "👍" else 0,
                                    comment=feedback.get("text", "")
                                )
                                st.success("Thank you for your feedback!")
                            except Exception as e:
                                st.error(f"Failed to submit feedback: {e}")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.markdown("Please try rephrasing your question or check your internet connection.")
                # Log the full error for debugging
                print(f"Chat error: {traceback.format_exc()}")

# Footer
st.markdown("""
---
<div style='text-align: center; color: #666;'>
    <small>Clare-AI v2.0 | Powered by LangGraph & OpenAI | CGU IST 345</small>
</div>
""", unsafe_allow_html=True)