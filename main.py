"""
Clare-AI - Teaching Assistant for Generative AI Course
Simplified Streamlit Interface using Modular Architecture
"""

import streamlit as st
import asyncio
import traceback
from functools import partial

# Import our modular components
from src.database.config import validate_env_vars, create_tables
from src.auth.authentication import (
    initialize_session_state,
    handle_sign_in,
    handle_profile_edit,
    is_user_signed_in,
    get_current_student_name,
    get_current_student_id,
    store_chat_to_db
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

# Sidebar for Profile Management
with st.sidebar:
    st.image("clare_pic-removebg.png", width=200)
    st.markdown("## 🤖 Clare-AI: Your IST 345 Assistant")

    # Authentication Section
    if not is_user_signed_in():
        if st.button("🔑 Sign In", use_container_width=True, type="primary"):
            handle_sign_in()
        st.markdown("*Please sign in to start using Clare-AI*")
    else:
        if st.button("✏️ Edit Profile", use_container_width=True):
            handle_profile_edit()
        student_name = get_current_student_name()
        st.markdown(f"**Welcome back, {student_name}!**")
        st.markdown(f"**Student ID:** {get_current_student_id()}")

    # Course Information
    st.markdown("""
    ### 📚 Course Information
    **IST 345.1 – Building Generative AI Applications**

    👥 **Contact Information:**
    - **Instructor**: Yan Li – [Yan.Li@cgu.edu](mailto:Yan.Li@cgu.edu)
    - **TA (Lab Tutoring)**: Kaijie Yu – [Kaijie.Yu@cgu.edu](mailto:Kaijie.Yu@cgu.edu)
    - **TA (Data Management)**: Yongjia Sun – [Yongjia.Sun@cgu.edu](mailto:Yongjia.Sun@cgu.edu)

    ### 🎯 How Clare-AI Helps
    - 📖 **Socratic Teaching**: Guides your thinking rather than giving direct answers
    - 🧠 **Personalized Learning**: Adapts to your background and progress
    - 📋 **Course Support**: Access to syllabus, assignments, and materials
    - 🔍 **Smart Search**: RAG-powered document retrieval
    """)

# Profile Form (if triggered)
if st.session_state.get("show_profile_form", False):
    from src.auth.profile_form import show_profile_form  # Import when needed
    show_profile_form()
    st.stop()

# Main Chat Interface
if not is_user_signed_in():
    st.info("🔑 Please sign in from the sidebar to start using Clare-AI")
    st.markdown("""
    ### 👋 Welcome to Clare-AI!

    Clare-AI is your intelligent teaching assistant for the **Generative AI Applications** course.

    **Features:**
    - 🎓 **Personalized Learning**: Tailored responses based on your profile
    - 📚 **Course Materials**: Access to lectures, readings, and assignments
    - 🤔 **Socratic Method**: Guided thinking instead of direct answers
    - 🔍 **Smart Search**: Find relevant information quickly

    **Getting Started:**
    1. Click "Sign In" in the sidebar
    2. Complete your learning profile
    3. Start asking questions about the course!
    """)
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