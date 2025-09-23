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
from src.database.config import validate_env_vars
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

# Custom CSS to adjust sidebar width
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        width: 400px !important;
    }

    /* Tooltip styles for status icon */
    .clare-tooltip {
        position: relative;
        display: inline-block;
        line-height: 1;
    }
    .clare-tooltip .clare-tooltip-text {
        visibility: hidden;
        opacity: 0;
        transition: opacity 0.15s ease-in-out;
        background: #111;
        color: #fff;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.8rem;
        white-space: normal;
        word-wrap: break-word;
        position: absolute;
        right: 0;
        top: -45px;
        z-index: 9999;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        max-width: 320px;
        line-height: 1.4;
    }
    .clare-tooltip:hover .clare-tooltip-text {
        visibility: visible;
        opacity: 1;
    }

    /* Dynamic student greeting styles */
    .dynamic-greeting {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: bold;
        font-size: 1.1rem;
        animation: subtle-glow 3s ease-in-out infinite alternate;
    }

    @keyframes subtle-glow {
        from { filter: brightness(1); }
        to { filter: brightness(1.1); }
    }

    /* Pulse animation for status icons */
    .status-pulse {
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
    }

    /* Smart Review button styles */
    .review-button {
        background: linear-gradient(45deg, #ff6b6b, #ee5a24);
        border: none;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(238, 90, 36, 0.3);
    }

    .review-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(238, 90, 36, 0.4);
        background: linear-gradient(45deg, #ff5252, #d63031);
    }

    /* Surprise button special styling */
    .surprise-button {
        background: linear-gradient(45deg, #feca57, #ff9ff3);
        border: none;
        color: white;
        padding: 10px 20px;
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 3px 10px rgba(254, 202, 87, 0.4);
        animation: rainbow-shift 5s ease-in-out infinite;
    }

    @keyframes rainbow-shift {
        0% { background: linear-gradient(45deg, #feca57, #ff9ff3); }
        25% { background: linear-gradient(45deg, #ff9ff3, #54a0ff); }
        50% { background: linear-gradient(45deg, #54a0ff, #5f27cd); }
        75% { background: linear-gradient(45deg, #5f27cd, #00d2d3); }
        100% { background: linear-gradient(45deg, #00d2d3, #feca57); }
    }

    .surprise-button:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 6px 15px rgba(254, 202, 87, 0.6);
    }

    /* Forgetting Curve Memory Strength Indicators */
    .memory-strength {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 8px;
        animation: memory-pulse 2s ease-in-out infinite;
    }

    .memory-urgent {
        background: linear-gradient(45deg, #ff4757, #ff3838);
        color: white;
        box-shadow: 0 2px 8px rgba(255, 71, 87, 0.4);
        animation: urgent-pulse 1.5s ease-in-out infinite;
    }

    .memory-medium {
        background: linear-gradient(45deg, #ffa502, #ff6348);
        color: white;
        box-shadow: 0 2px 8px rgba(255, 165, 2, 0.4);
    }

    .memory-stable {
        background: linear-gradient(45deg, #2ed573, #1dd1a1);
        color: white;
        box-shadow: 0 2px 8px rgba(46, 213, 115, 0.4);
    }

    @keyframes memory-pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.05); opacity: 0.9; }
    }

    @keyframes urgent-pulse {
        0%, 100% { transform: scale(1); box-shadow: 0 2px 8px rgba(255, 71, 87, 0.4); }
        50% { transform: scale(1.08); box-shadow: 0 4px 12px rgba(255, 71, 87, 0.7); }
    }

    /* Time interval indicators */
    .time-interval {
        display: inline-block;
        background: rgba(75, 139, 190, 0.15);
        color: #4B8BBE;
        padding: 2px 6px;
        border-radius: 8px;
        font-size: 0.7rem;
        margin-right: 8px;
        border: 1px solid rgba(75, 139, 190, 0.3);
    }

    /* Retention progress bar */
    .retention-bar {
        width: 100%;
        height: 6px;
        background: #f1f3f4;
        border-radius: 3px;
        margin: 8px 0;
        overflow: hidden;
    }

    .retention-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    .retention-urgent {
        background: linear-gradient(90deg, #ff4757, #ff3838);
        width: 25%;
    }

    .retention-medium {
        background: linear-gradient(90deg, #ffa502, #ff6348);
        width: 60%;
    }

    .retention-stable {
        background: linear-gradient(90deg, #2ed573, #1dd1a1);
        width: 90%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Command handler for multi-step actions
if "next_action" in st.session_state:
    action, value = st.session_state.pop("next_action")
    if action == "start_review":
        st.session_state.chat_history = []
        st.session_state.pending_prompt = value
        st.rerun()

# Validate environment variables (but skip database initialization to avoid startup blocking)
try:
    validate_env_vars()
    # Note: Tables are assumed to exist already - removed create_tables() to prevent startup blocking
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
            st.rerun()  # Refresh UI

    # Signed-in summary with user status - Card Design
    if is_user_signed_in():
        with st.container(border=True):
            # Fetch all required data
            student_name = get_current_student_name()
            student_id = get_current_student_id()
            user_status = check_user_status(student_id)

            # Determine icon and tooltip text based on profile status
            if user_status["is_new_user"] or not user_status["is_profile_complete"]:
                status_icon = "⚠️"
                status_tooltip = "Profile incomplete"
            else:
                status_icon = "✅"
                status_tooltip = "Profile complete"

            # Use column layout for elegant alignment of name and status icon
            col1, col2 = st.columns([0.85, 0.15])

            with col1:
                st.markdown(f'<div class="dynamic-greeting">Hello, {student_name}!</div>', unsafe_allow_html=True)

            with col2:
                # Right-aligned icon with hover tooltip
                st.markdown(
                    f"""
                    <div style='display: flex; justify-content: flex-end;'>
                        <span class="clare-tooltip status-pulse" aria-label="{status_tooltip}" style="font-size: 1.2rem; cursor: help;">
                            {status_icon}
                            <span class="clare-tooltip-text">{status_tooltip}</span>
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # Secondary information in one clean line
            last_login_str = ""
            if user_status.get("last_login"):
                last_login_str = f" • Last login: {user_status['last_login'].strftime('%m/%d/%Y')}"

            st.caption(f"ID: {student_id}{last_login_str}")

        # Add the Smart Review feature here, visible only when signed in

        # Smart Review header with tooltip
        st.markdown(
            """
            <div style="display: flex; align-items: center; margin-bottom: 3px;">
                <h3 style="margin: 0; color: #1f2937;">🧠 Smart Review</h3>
                <span class="clare-tooltip" style="margin-left: 8px; cursor: help; color: #6b7280;">
                    ℹ️
                    <span class="clare-tooltip-text" style="width: 280px; left: -140px;">
                        Based on the forgetting curve, Clare has selected topics you might be forgetting from your learning history and interaction patterns.
                    </span>
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Forgetting curve timeline visualization
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #f8f9fa, #e9ecef); padding: 12px; border-radius: 8px; margin: 6px 0;">
                <div style="font-size: 0.85rem; font-weight: bold; color: #495057; margin-bottom: 8px;">
                    📊 Current Review Distribution (T+7 Schedule)
                </div>
                <div style="display: flex; align-items: center; gap: 15px; font-size: 0.75rem;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 60px; height: 4px; background: linear-gradient(90deg, #ff4757, #ff3838); margin-right: 5px; border-radius: 2px;"></div>
                        <span>W-4: 35%</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 40px; height: 4px; background: linear-gradient(90deg, #ffa502, #ff6348); margin-right: 5px; border-radius: 2px;"></div>
                        <span>W-2: 20%</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="width: 20px; height: 4px; background: linear-gradient(90deg, #2ed573, #1dd1a1); margin-right: 5px; border-radius: 2px;"></div>
                        <span>W-1: 12%</span>
                    </div>
                    <div style="margin-left: auto; color: #6c757d;">
                        💡 Higher weights = higher forgetting risk
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 1. Define the review topics with forgetting curve metadata
        review_topics = [
            {
                "title": "Review: Main Concept of Lab 3",
                "original_question": "I've read the instructions for Lab 3, but what is the main concept we're supposed to be learning here?",
                "key": "lab1_review",
                "time_interval": "T+7",
                "memory_strength": "urgent",
                "retention_level": 25,
                "last_reviewed": "7 days ago",
                "weight": "35%"
            },
            {
                "title": "Review: Effective Prompt Engineering",
                "original_question": "I understand what prompt engineering is, but what specifically makes a prompt effective versus ineffective?",
                "key": "prompt_review",
                "time_interval": "T+14",
                "memory_strength": "medium",
                "retention_level": 60,
                "last_reviewed": "3 days ago",
                "weight": "20%"
            },
            {
                "title": "Review: Objective LLM Evaluation",
                "original_question": "How can we objectively evaluate an LLM's performance when the output quality seems so subjective?",
                "key": "eval_review",
                "time_interval": "T+7",
                "memory_strength": "stable",
                "retention_level": 90,
                "last_reviewed": "1 day ago",
                "weight": "12%"
            }
        ]

        # 2. Define an expanded list of random topics
        random_prompts = [
            "Explain the difference between RAG and fine-tuning.",
            "What is Self-RAG and how does it work?",
            "Summarize the key ideas behind Constitutional AI.",
            "What are the main components of an AI Agent?",
            "Describe the concept of RAG-Fusion.",
            "What is the role of a vector store like pgvector in a RAG system?",
            "How does LangGraph help in building complex AI agents compared to a simple LangChain chain?",
            "What are hallucinations in LLMs and how can they be mitigated?",
            "Explain the concept of 'Maximal Marginal Relevance' (MMR) in document retrieval.",
            "What is the difference between an AI Agent and a simple chatbot?",
            "What is an API, and how do we use it to access models like GPT-4?",
            "What is the purpose of an embedding model like text-embedding-3-large?"
        ]

        # Callback to set the next_action for the command handler
        def trigger_review_session(prompt):
            st.session_state.next_action = ("start_review", prompt)

        # 3. Create the expanders with the new behavior and forgetting curve indicators
        for topic in review_topics:
            # Enhanced title with memory strength indicator
            strength_class = f"memory-strength memory-{topic['memory_strength']}"
            strength_text = {"urgent": "🔥 URGENT", "medium": "⚠️ REVIEW", "stable": "✅ STABLE"}[topic['memory_strength']]

            enhanced_title = f"{topic['title']}"

            with st.expander(enhanced_title):
                # Memory status header with visual indicators
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; margin-bottom: 12px;">
                        <span class="time-interval">{topic['time_interval']}</span>
                        <span class="{strength_class}">{strength_text}</span>
                        <span style="margin-left: auto; font-size: 0.8rem; color: #666;">
                            Weight: {topic['weight']} | Last: {topic['last_reviewed']}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Retention progress bar
                retention_class = f"retention-{topic['memory_strength']}"
                st.markdown(
                    f"""
                    <div style="margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #666; margin-bottom: 4px;">
                            <span>Memory Retention</span>
                            <span>{topic['retention_level']}%</span>
                        </div>
                        <div class="retention-bar">
                            <div class="retention-fill {retention_class}"></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.caption(f'''You previously asked: "{topic["original_question"]}"''')

                # Create a styled container for the button
                st.markdown('<div style="text-align: center; margin: 10px 0;">', unsafe_allow_html=True)
                if st.button("📚 Review this topic", key=topic["key"], on_click=trigger_review_session, args=[topic["original_question"]], type="primary", use_container_width=True):
                    pass  # Action handled by on_click
                st.markdown('</div>', unsafe_allow_html=True)

        # 4. Create the "Personal Quiz" button with tooltip explanation
        import random
        st.markdown('<div style="text-align: center; margin: 15px 0;">', unsafe_allow_html=True)

        # Personal Quiz button with tooltip
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: flex-start; width: 100%; margin-bottom: 8px;">
                <span style="font-weight: 500; color: #374151;">🎲 Personal Quiz</span>
                <span class="clare-tooltip" style="margin-left: 6px; cursor: help; color: #6b7280;">
                    ℹ️
                    <span class="clare-tooltip-text" style="width: 300px; left: -150px;">
                        Clare analyzes your chat history and learning patterns to randomly select a personalized question that challenges your understanding of previously discussed topics.
                    </span>
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("🎲 Test your memory", type="primary", use_container_width=True, key="personal_quiz_btn"):
            random_prompt = random.choice(random_prompts)
            trigger_review_session(random_prompt)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


    # Welcome and onboarding moved from center to sidebar
    with st.expander("👋 Welcome & Getting Started", expanded= not is_user_signed_in()):
        st.markdown("""
        Clare-AI is your intelligent teaching assistant for the **IST 345 Generative AI Applications** course.
        - 🎓 Personalized Learning: Tailored responses based on your profile
        - 📚 Course Materials: Access to lectures, readings, and assignments
        - 🤔 Socratic Method: Guided thinking instead of direct answers
        - 🔍 Smart Search: Find relevant information quickly

        **Getting Started**
        1. Click "Sign In" above
        2. Complete your learning profile (if new user)
        3. Start asking questions about the course!
        """)

    # Compact info using expanders
    with st.expander("📚 Course Info", expanded=False):
        st.markdown("**IST 345 - Building Generative AI Applications**")
        st.markdown("""
        - Instructor: Yan Li - [Yan.Li@cgu.edu](mailto:Yan.Li@cgu.edu)
        - TA (Lab): Kaijie Yu - [Kaijie.Yu@cgu.edu](mailto:Kaijie.Yu@cgu.edu)
        - TA (Data): Yongjia Sun - [Yongjia.Sun@cgu.edu](mailto:Yongjia.Sun@cgu.edu)
        """)

    with st.expander("🎯 How Clare Helps", expanded=False):
        st.markdown("""
        - Socratic guidance, not direct answers
        - Personalized to your profile
        - Syllabus and materials shortcuts
        - Smart search across course docs
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

# Chat input (supports queued prompts from Smart Review buttons)
pending_prompt = st.session_state.pop("pending_prompt", None)
user_chat_input = st.chat_input("Ask Clare-AI about the course...")
prompt = pending_prompt or user_chat_input

if prompt:
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