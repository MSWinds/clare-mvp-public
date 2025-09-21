import streamlit as st
from dotenv import load_dotenv
# Import the main LangGraph workflow entry point - moved to lazy loading
# from agentic_workflow import get_workflow
import asyncio
from langchain_core.tracers.context import collect_runs
# LangSmith Client enables feedback tracking and run tracing (for evaluation, debugging)
from langsmith import Client 
from streamlit_feedback import streamlit_feedback 
from functools import partial 
# Traceback is used to print the full traceback of an error
import traceback 

from sqlalchemy import create_engine, Table, Column, String, Text, MetaData, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
import uuid
import os
import json

# Load environment variables
load_dotenv()

# DB connection - moved to lazy initialization
@st.cache_resource
def init_database():
    connection_string = os.getenv("DATABASE_URL")
    engine = create_engine(connection_string)
    metadata = MetaData()
    
    # Define table structure
    chat_table = Table(
        'chat_history', metadata,
        Column('id', UUID(as_uuid=True), primary_key=True),
        Column('student_id', Text, nullable=False),
        Column('user_input', Text, nullable=False),
        Column('ai_response', Text, nullable=False),
        Column('timestamp', DateTime(timezone=True), default=datetime.now(timezone.utc))
    )
    
    metadata.create_all(engine)
    return engine, chat_table

# Database will be initialized when first needed
engine = None
chat_table = None

def store_chat_to_db(student_id, user_input, ai_response):
    global engine, chat_table
    if engine is None:
        engine, chat_table = init_database()
    
    try:
        with engine.connect() as conn:
            insert_stmt = chat_table.insert().values(
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
    global engine, chat_table
    if engine is None:
        engine, chat_table = init_database()
    
    try:
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
            interaction_count = result.interaction_count if result else 0
            
            # Trigger update after 5 interactions since last profile update
            should_trigger = interaction_count >= 5
            
            if should_trigger:
                print(f"Profile update triggered for {student_id} after {interaction_count} interactions")
            
            return should_trigger
            
    except Exception as e:
        print(f"Error checking profile update trigger: {e}")
        return False

def trigger_profile_update(student_id: str):
    """
    Trigger an asynchronous profile update for the given student.
    This runs in the background to avoid delaying the chat response.
    """
    import asyncio
    import threading
    
    def run_profile_update():
        try:
            from profile_analyzer import analyze_and_update_profile
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the profile update
            result = loop.run_until_complete(
                analyze_and_update_profile(student_id, analysis_type="interaction")
            )
            
            if result.get("save_status") == "success":
                evidence_count = result.get("evidence_count", 0)
                print(f"Background profile update completed for {student_id}: {evidence_count} evidence items")
            else:
                print(f"Background profile update failed for {student_id}: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"Background profile update error for {student_id}: {e}")
        finally:
            loop.close()
    
    # Run profile update in background thread
    update_thread = threading.Thread(target=run_profile_update, daemon=True)
    update_thread.start()
    print(f"Started background profile update for {student_id}")

# Initialize LangSmith client lazily
@st.cache_resource
def init_langsmith_client():
    try:
        client = Client()
        print("LangSmith Client Initialized Successfully.") 
        return client
    except Exception as e:
        # Warn once during startup if client initialization fails
        st.warning(f"Could not initialize LangSmith client. Feedback submission may not work. Error: {e}")
        print(f"LangSmith Client Initialization Failed: {e}") 
        return None

# Get client when needed
client = None  # Will be initialized lazily

# Page config
st.set_page_config(
    page_title='Clare-AI - TA Assistant',
    page_icon="clare_pic.jpg",
    layout="wide"
)

# Main title
st.markdown(
    """
    <h1 style='text-align: center; color: #4B8BBE;'>
        <span style='color:#306998;'>Clare-AI</span> - TA Assistant
    </h1>
    """,
    unsafe_allow_html=True
)
# Initialize profile session state
if "profile_data" not in st.session_state:
    st.session_state["profile_data"] = None
if "student_id" not in st.session_state:
    st.session_state["student_id"] = ""

# Create the sidebar section
with st.sidebar:
    st.image("clare_pic-removebg.png")  # Clare logo
    st.markdown("## 🤖 Clare-AI: Your IST 345 Assistant")
    
    # Show Sign In or Edit Profile button based on profile status
    if st.session_state["profile_data"] is None:
        if st.button("🔑 Sign In", use_container_width=True, type="primary"):
            st.session_state["show_profile_form"] = True
            st.rerun()
        st.markdown("*Please sign in to start using Clare-AI*")
    else:
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.session_state["show_profile_form"] = True
            st.rerun()
        student_name = st.session_state["profile_data"].get("name", "Student")
        st.markdown(f"**Welcome back, {student_name}!**")
        st.markdown(f"**Student ID:** {st.session_state['student_id']}")
    
    st.markdown("""
    Welcome to **Clare-AI**, your dedicated assistant for **CGU IST 345.1 – Building Generative AI Applications**.
    
    - 👥 **Instructor & TA Contacts**:
    - **Instructor**: Yan Li – [Yan.Li@cgu.edu](mailto:Yan.Li@cgu.edu)
    - **TA (Lab Tutoring)**: Kaijie Yu – [Kaijie.Yu@cgu.edu](mailto:Kaijie.Yu@cgu.edu)
    - **TA (Data Management)**: Yongjia Sun – [Yongjia.Sun@cgu.edu](mailto:Yongjia.Sun@cgu.edu)

    I'm here to support your learning journey by:
    - 📘 **Course Materials**: Access lecture notes, reading lists, and assignment guidelines.
    - 🧠 **Conceptual Understanding**: Get explanations on RNNs, LSTMs, transformers, and other neural network architectures.
    - 🛠️ **Practical Questions**: Assistance with coding assignments and model implementation.
                
    **Clare-AI is designed to guide your reasoning process rather than provide direct answers**, helping you develop critical thinking skills. By analyzing your questions and responses, Clare-AI offers feedback to improve your understanding and explore new problem-solving strategies.

    Let's explore the fascinating world of generative AI together!
    """)

    # Refresh button
    if st.button("New Conversation 🔄", use_container_width=True):

        # Clear chat history
        st.session_state.chat_history = []
        # Remove all feedback keys from session state
        # If these feedback keys weren't cleared, they could incorrectly map to new messages in the next conversation
        keys_to_delete = [key for key in st.session_state.keys() if key.startswith("feedback_")]
        for key in keys_to_delete:
            del st.session_state[key]
        
        # Restart the app to show a fresh interface
        st.rerun()

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Initialize profile form state
if "show_profile_form" not in st.session_state:
    st.session_state["show_profile_form"] = False

# --- Profile Data Functions - Connected to Profile Analyzer ---
def convert_questionnaire_to_evidence(profile_data):
    """Convert UI questionnaire responses to evidence items for profile_analyzer"""
    from datetime import datetime
    import json
    
    evidence_items = []
    current_time = datetime.now().isoformat() + "Z"
    
    # Convert each questionnaire response to evidence items with proper JSON serialization
    
    # Basic Info
    if profile_data.get("name"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "basic_info",
            "field": "name",
            "value": json.dumps(profile_data["name"]) if isinstance(profile_data["name"], (dict, list)) else profile_data["name"],
            "confidence": 1.0,
            "weight": 1.0,
            "note": "Q1: Student name"
        })
    
    if profile_data.get("course"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "basic_info", 
            "field": "enrollment",
            "value": json.dumps({"course": profile_data["course"]}) if profile_data["course"] else "{}",
            "confidence": 1.0,
            "weight": 1.0,
            "note": "Q4: Course enrollment"
        })
    
    # Technical Profile
    if profile_data.get("academic_background"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "technical_profile",
            "field": "prior_education",
            "value": profile_data["academic_background"],
            "confidence": 1.0,
            "weight": 1.0,
            "note": "Q5: Academic background"
        })
    
    if profile_data.get("programming_experience"):
        # Serialize list to JSON
        programming_value = json.dumps(profile_data["programming_experience"]) if isinstance(profile_data["programming_experience"], list) else profile_data["programming_experience"]
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "technical_profile",
            "field": "programming_experience",
            "value": programming_value,
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q8: Programming experience"
        })
    
    if profile_data.get("tech_familiarity"):
        tech_value = json.dumps(profile_data["tech_familiarity"]) if isinstance(profile_data["tech_familiarity"], list) else profile_data["tech_familiarity"]
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "technical_profile",
            "field": "ai_tools_used",
            "value": tech_value,
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q9: Technology familiarity"
        })
    
    # Cognitive Profile  
    if profile_data.get("study_hours"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "cognitive_profile",
            "field": "learning_pace",
            "value": "intensive" if "More than 20" in profile_data["study_hours"] else 
                     "moderate" if "10–20" in profile_data["study_hours"] else "relaxed",
            "confidence": 0.8,
            "weight": 1.0,
            "note": f"Q14: {profile_data['study_hours']} study hours per week"
        })
    
    # Learning Style
    if profile_data.get("learning_style"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "learning_style",
            "field": "preferred_formats",
            "value": json.dumps([profile_data["learning_style"].lower()]),
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q11: Preferred learning style"
        })
    
    if profile_data.get("learning_goals"):
        goals_value = json.dumps(profile_data["learning_goals"]) if isinstance(profile_data["learning_goals"], list) else profile_data["learning_goals"]
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "learning_style",
            "field": "study_patterns",
            "value": goals_value,
            "confidence": 0.85,
            "weight": 1.0,
            "note": "Q10: Learning goals"
        })
    
    if profile_data.get("motivation"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "learning_style",
            "field": "motivation",
            "value": profile_data["motivation"].lower().replace(" ", "_"),
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q22: Primary learning motivation"
        })
    
    # Challenges & Needs
    if profile_data.get("learning_challenges"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "challenges_needs",
            "field": "pain_points",
            "value": json.dumps([profile_data["learning_challenges"]]),
            "confidence": 0.8,
            "weight": 1.0,
            "note": "Q15: Biggest learning challenges"
        })
    
    if profile_data.get("ai_support"):
        support_value = json.dumps(profile_data["ai_support"]) if isinstance(profile_data["ai_support"], list) else profile_data["ai_support"]
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "challenges_needs",
            "field": "support_needed",
            "value": support_value,
            "confidence": 0.85,
            "weight": 1.0,
            "note": "Q12: Expected AI assistant support"
        })
    
    # AI Strategy
    if profile_data.get("personality"):
        guidance_mode = "encouraging" if profile_data["personality"] == "Introverted" else "collaborative"
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "ai_strategy",
            "field": "guidance_mode",
            "value": guidance_mode,
            "confidence": 0.7,
            "weight": 1.0,
            "note": f"Q21: {profile_data['personality']} personality"
        })
    
    if profile_data.get("clare_motivation"):
        motivation_value = json.dumps(profile_data["clare_motivation"]) if isinstance(profile_data["clare_motivation"], list) else profile_data["clare_motivation"]
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "ai_strategy",
            "field": "feedback_modes",
            "value": motivation_value,
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q23: Clare motivation preferences"
        })
    
    # Career
    if profile_data.get("industry_interest"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "career",
            "field": "interests",
            "value": json.dumps([profile_data["industry_interest"]]),
            "confidence": 0.9,
            "weight": 1.0,
            "note": "Q18: Industry interest"
        })
    
    if profile_data.get("career_goal"):
        evidence_items.append({
            "source": "questionnaire",
            "ts": current_time,
            "dimension": "career",
            "field": "goals",
            "value": json.dumps([profile_data["career_goal"]]),
            "confidence": 0.85,
            "weight": 1.0,
            "note": "Q19: Career goal"
        })
    
    return evidence_items

def process_questionnaire_with_profile_analyzer(profile_data):
    """Process questionnaire data through profile_analyzer and store in database"""
    import asyncio
    import threading
    from profile_analyzer import analyze_and_update_profile
    
    def run_profile_analysis():
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            student_id = profile_data["student_id"]
            
            # Convert questionnaire to evidence format
            evidence_items = convert_questionnaire_to_evidence(profile_data)
            
            print(f"🔄 Processing questionnaire for {student_id} with {len(evidence_items)} evidence items")
            
            # Create a special questionnaire processing mode
            result = loop.run_until_complete(
                process_questionnaire_evidence(student_id, evidence_items)
            )
            
            if result.get("save_status") == "success":
                print(f"✅ Questionnaire profile created for {student_id}")
            else:
                print(f"❌ Questionnaire processing failed for {student_id}: {result.get('error', 'Unknown error')}")
                
            return result
            
        except Exception as e:
            print(f"❌ Questionnaire processing error for {student_id}: {e}")
            return {"error": str(e)}
        finally:
            loop.close()
    
    # Run in background thread to avoid blocking UI
    analysis_thread = threading.Thread(target=run_profile_analysis, daemon=True)
    analysis_thread.start()
    print(f"🚀 Started questionnaire processing for {profile_data['student_id']}")

async def process_questionnaire_evidence(student_id, evidence_items):
    """Process questionnaire evidence directly without chat history analysis"""
    # Import only what we need to avoid heavy workflow imports
    from profile_analyzer import get_structured_profile, PROFILE_MERGE_SYSTEM_PROMPT
    
    # Initialize LLM locally instead of importing from profile_analyzer (which has heavy imports)
    from langchain_openai import ChatOpenAI
    llm_gpt = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))
    
    global engine, chat_table
    if engine is None:
        engine, chat_table = init_database()

    
    try:
        # Get current profile (empty for new users)
        current_profile = get_structured_profile(student_id) or {}
        
        # Use the merge prompt from profile_analyzer
        user_prompt = f"""current_profile = {json.dumps(current_profile, indent=2)}
evidence = {json.dumps(evidence_items, indent=2)}"""
        
        messages = [
            {"role": "system", "content": PROFILE_MERGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call LLM to merge questionnaire evidence  
        response = await llm_gpt.ainvoke(messages)
        
        # Parse response - should be {"text_summary": "..."}
        try:
            updated_profile = json.loads(response.content.strip())
            if "text_summary" not in updated_profile:
                # Fallback if LLM didn't follow format
                updated_profile = {"text_summary": response.content.strip()}
        except json.JSONDecodeError:
            # Fallback if response isn't valid JSON
            updated_profile = {"text_summary": response.content.strip()}
        
        # Ensure text summary format for MVP
        complete_profile = updated_profile
        
        # Check if student profile exists first, then update or insert
        check_stmt = text("SELECT id FROM student_profiles WHERE student_id = :student_id")
        
        with engine.connect() as conn:
            existing = conn.execute(check_stmt, {"student_id": student_id}).fetchone()
            
            if existing:
                # Update existing profile
                update_stmt = text("""
                    UPDATE student_profiles 
                    SET profile_summary = :profile_summary, timestamp = :timestamp
                    WHERE student_id = :student_id
                """)
                conn.execute(update_stmt, {
                    "student_id": student_id,
                    "profile_summary": json.dumps(complete_profile),
                    "timestamp": datetime.now(timezone.utc)
                })
            else:
                # Insert new profile
                insert_stmt = text("""
                    INSERT INTO student_profiles (id, student_id, profile_summary, timestamp)
                    VALUES (:id, :student_id, :profile_summary, :timestamp)
                """)
                conn.execute(insert_stmt, {
                    "id": uuid.uuid4(),
                    "student_id": student_id,
                    "profile_summary": json.dumps(complete_profile),
                    "timestamp": datetime.now(timezone.utc)
                })
            conn.commit()
        
        return {
            "student_id": student_id,
            "evidence_count": len(evidence_items),
            "updated_profile": updated_profile,
            "save_status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {
            "student_id": student_id,
            "error": str(e),
            "save_status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# --- Profile Questionnaire Form ---
def show_profile_form():
    """Display the student profile questionnaire form"""
    
    # Get existing profile data for editing
    existing_data = st.session_state["profile_data"] or {}
    
    with st.form("student_profile_form"):
        st.header("🎓 Welcome! Let’s personalize your learning with Clare")
        st.markdown("Tell us a bit about yourself so Clare can support your study journey")
        
        # Part 1: Basic Information (Required)
        st.subheader("📋 Part 1. Basic Information")
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Q1. What is your full name?", value=existing_data.get("name", ""))
            student_id = st.text_input("Q2. What is your Student ID? **(Required)**", value=existing_data.get("student_id", ""))
        
        with col2:
            email = st.text_input("Q3. What is your email address?", value=existing_data.get("email", ""))
            course = st.text_input("Q4. Which course or program are you enrolled in?", value=existing_data.get("course", ""))
        
        # Part 2: Academic & Technical Background
        st.subheader("🎯 Part 2. Academic & Technical Background")
        
        academic_bg = st.selectbox("Q5. Academic background:", 
            ["", "Humanities / Arts", "Social Sciences", "Education", "Business / Management", 
             "Science / Engineering", "Medicine / Health Sciences", "Other"],
            index=0 if not existing_data.get("academic_background") else 
                  ["", "Humanities / Arts", "Social Sciences", "Education", "Business / Management", 
                   "Science / Engineering", "Medicine / Health Sciences", "Other"].index(existing_data.get("academic_background", "")))
        
        study_level = st.selectbox("Q6. Current study level:",
            ["", "Master's", "Doctoral", "Postdoctoral / Research Fellow", "Other"],
            index=0 if not existing_data.get("study_level") else
                  ["", "Master's", "Doctoral", "Postdoctoral / Research Fellow", "Other"].index(existing_data.get("study_level", "")))
        
        cs_experience = st.selectbox("Q7. Have you studied computer science or related fields?",
            ["", "Yes", "No"],
            index=0 if not existing_data.get("cs_experience") else
                  ["", "Yes", "No"].index(existing_data.get("cs_experience", "")))
        
        programming_exp = st.multiselect("Q8. Programming experience (check all that apply):",
            ["Python", "R", "Java / C++", "SQL / Databases", "None", "Other"],
            default=existing_data.get("programming_experience", []))
        
        tech_familiarity = st.multiselect("Q9. Emerging technologies familiar with:",
            ["AI / Machine Learning", "Cloud Computing", "IoT", "Blockchain", "Cybersecurity", "Other"],
            default=existing_data.get("tech_familiarity", []))
        
        # Part 3: Learning Goals & Preferences
        st.subheader("🎯 Part 3. Learning Goals & Preferences")
        
        learning_goals = st.multiselect("Q10. Main learning goals:",
            ["Understanding fundamental concepts", "Improving grades / exam preparation", 
             "Developing practical skills", "Research / academic writing", 
             "Career development", "Other"],
            default=existing_data.get("learning_goals", []))
        
        learning_style = st.selectbox("Q11. Preferred learning style:",
            ["", "Visual", "Reading/Writing", "Auditory", "Kinesthetic", "Mixed / No strong preference"],
            index=0 if not existing_data.get("learning_style") else
                  ["", "Visual", "Reading/Writing", "Auditory", "Kinesthetic", "Mixed / No strong preference"].index(existing_data.get("learning_style", "")))
        
        ai_support = st.multiselect("Q12. Expected AI assistant support:",
            ["Personalized learning paths", "Automated grading and feedback", 
             "Academic writing support", "Data analysis / technical guidance",
             "Time management and reminders", "Other"],
            default=existing_data.get("ai_support", []))
        
        study_plan = st.selectbox("Q13. Would you like Clare to help design a study plan?",
            ["", "Yes", "No"],
            index=0 if not existing_data.get("study_plan") else
                  ["", "Yes", "No"].index(existing_data.get("study_plan", "")))
        
        # Part 4: Study Habits
        st.subheader("📚 Part 4. Study Habits")
        
        study_hours = st.selectbox("Q14. Average study hours per week:",
            ["", "Less than 5 hours", "5–10 hours", "10–20 hours", "More than 20 hours"],
            index=0 if not existing_data.get("study_hours") else
                  ["", "Less than 5 hours", "5–10 hours", "10–20 hours", "More than 20 hours"].index(existing_data.get("study_hours", "")))
        
        learning_challenges = st.text_area("Q15. Biggest challenges in learning:",
            value=existing_data.get("learning_challenges", ""))
        
        study_location = st.multiselect("Q16. Preferred study locations:",
            ["Library", "Café", "Home", "Online", "Other"],
            default=existing_data.get("study_location", []))
        
        study_preference = st.selectbox("Q17. Study preference:",
            ["", "Independent study", "Group study", "Mixed"],
            index=0 if not existing_data.get("study_preference") else
                  ["", "Independent study", "Group study", "Mixed"].index(existing_data.get("study_preference", "")))
        
        # Part 5: Interests & Career Development
        st.subheader("🚀 Part 5. Interests & Career Development")
        
        industry_interest = st.selectbox("Q18. Most interested industry:",
            ["", "Education", "Technology / IT", "Business / Management", 
             "Healthcare", "Finance", "Public Sector / Nonprofit", "Other"],
            index=0 if not existing_data.get("industry_interest") else
                  ["", "Education", "Technology / IT", "Business / Management", 
                   "Healthcare", "Finance", "Public Sector / Nonprofit", "Other"].index(existing_data.get("industry_interest", "")))
        
        career_goal = st.text_area("Q19. Career goal:",
            value=existing_data.get("career_goal", ""))
        
        career_support = st.multiselect("Q20. Career support from AI:",
            ["Internship recommendations", "Career skill development resources",
             "Resume feedback / mock interviews", "Networking and research collaboration", "Other"],
            default=existing_data.get("career_support", []))
        
        # Part 6: Personality & Motivation
        st.subheader("🧠 Part 6. Personality & Motivation")
        
        personality = st.selectbox("Q21. Personality type:",
            ["", "Introverted", "Extroverted", "Balanced"],
            index=0 if not existing_data.get("personality") else
                  ["", "Introverted", "Extroverted", "Balanced"].index(existing_data.get("personality", "")))
        
        motivation = st.selectbox("Q22. Primary learning motivation:",
            ["", "Interest and curiosity", "Academic performance / graduation requirements",
             "Future career development", "Family / social expectations", "Other"],
            index=0 if not existing_data.get("motivation") else
                  ["", "Interest and curiosity", "Academic performance / graduation requirements",
                   "Future career development", "Family / social expectations", "Other"].index(existing_data.get("motivation", "")))
        
        clare_motivation = st.multiselect("Q23. How should Clare motivate you:",
            ["Learning reminders", "Progress tracking with milestones",
             "Achievement badges / rewards", "Daily encouragement and positive feedback", "Other"],
            default=existing_data.get("clare_motivation", []))
        
        # Form submission buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            submit_button = st.form_submit_button("💾 Save Profile", type="primary")
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel")
        with col3:
            if st.session_state["profile_data"]:
                clear_button = st.form_submit_button("🗑️ Clear All")
        
        # Handle form submission
        if submit_button:
            if not student_id.strip():
                st.error("⚠️ Student ID is required!")
                return False
            
            # Save profile data to session state
            profile_data = {
                "name": name,
                "student_id": student_id.strip(),
                "email": email,
                "course": course,
                "academic_background": academic_bg,
                "study_level": study_level,
                "cs_experience": cs_experience,
                "programming_experience": programming_exp,
                "tech_familiarity": tech_familiarity,
                "learning_goals": learning_goals,
                "learning_style": learning_style,
                "ai_support": ai_support,
                "study_plan": study_plan,
                "study_hours": study_hours,
                "learning_challenges": learning_challenges,
                "study_location": study_location,
                "study_preference": study_preference,
                "industry_interest": industry_interest,
                "career_goal": career_goal,
                "career_support": career_support,
                "personality": personality,
                "motivation": motivation,
                "clare_motivation": clare_motivation
            }
            
            st.session_state["profile_data"] = profile_data
            st.session_state["student_id"] = student_id.strip()
            st.session_state["show_profile_form"] = False
            
            # Process questionnaire through profile_analyzer and store in database
            try:
                process_questionnaire_with_profile_analyzer(profile_data)
                st.success("✅ Profile saved and processing started!")
                st.info("🔄 Your learning profile is being created in the background...")
            except Exception as e:
                st.error(f"⚠️ Profile saved to session, but processing failed: {e}")
                print(f"Questionnaire processing error: {e}")
            
            st.rerun()
        
        elif cancel_button:
            st.session_state["show_profile_form"] = False
            st.rerun()
        
        elif st.session_state["profile_data"] and 'clear_button' in locals() and clear_button:
            st.session_state["profile_data"] = None
            st.session_state["student_id"] = ""
            st.session_state["show_profile_form"] = False
            st.warning("🗑️ Profile cleared!")
            st.rerun()

# Show profile form if triggered
if st.session_state.get("show_profile_form", False):
    show_profile_form()
    # Don't show the rest of the app while the form is displayed
    st.stop()

# Block chat interface if not signed in
if st.session_state["profile_data"] is None:
    st.info("🔑 Please sign in from the sidebar to start using Clare-AI")
    st.stop()

# --- Feedback Submission Function ---
def submit_feedback(user_response, run_id, client):
    """
    Submits thumbs-up/down feedback to LangSmith for a given run ID.
    This helps evaluate the performance of the LLM workflow after user interaction.
    """

    # If client is None (init failed) or run_id is missing, skip silently.
    if not client or not run_id:
        print(f"Debug (submit_feedback skipped): Client available: {client is not None}, Run ID: {run_id}")
        return
    
    try:
        # Map emoji score to numeric value expected by LangSmith
        score_map = {"👍": 1, "👎": 0}
        score = score_map.get(user_response.get("score"))
        comment = user_response.get("text")

        # Only submit feedback if there's a valid thumbs-up or thumbs-down
        # Currently, the client automatically associates the feedback with this LangSmith account credentials from API key
        # If you want to associate feedback with a different LangSmith account, you can do so by setting the `user` parameter
        # to a different value (e.g., a user ID or email)
        if score is not None:
            feedback_result = client.create_feedback(
                run_id=run_id,
                key="user_thumb_feedback",       # Descriptive key
                score=score,                     # Numeric score (1 or 0)
                comment=comment,                 # Optional user explanation
                value=user_response.get("score") # Store the emoji
            )
            print(f"Feedback submitted: Run ID: {run_id}, Score: {score}, Comment: {comment}, Result: {feedback_result}") 
        else:
            # Skip submission if user didn’t click thumbs-up or down
             print(f"Feedback skipped (no score): Run ID: {run_id}, Response: {user_response}")

    except Exception as e:
        # If LangSmith API fails, show error in UI and log the exception
        st.error(f"Failed to submit feedback to LangSmith: {e}")
        print(f"Error submitting feedback: Run ID: {run_id}, Exception: {e}")

# --- Lazy load workflow when needed ---
@st.cache_resource
def get_compiled_workflow():
    from agentic_workflow import get_workflow
    return get_workflow().compile()

# --- Async function to get LLM response AND LangSmith run_id from the workflow ---
async def get_drucker_response_with_run_id(user_input):
    """
    Executes the LangGraph workflow with the user's input and captures:
    1. The AI-generated response.
    2. The LangSmith run ID (for feedback/tracing).

    This function supports streaming and error handling for feedback and traceability.
    """
    # Retrieve and compile the LangGraph workflow
    graph = get_compiled_workflow()    # Cached if already built
    final_state = None                  # Holds the last emitted state from the graph
    run_id = None                        # LangSmith run ID (used for tracing/feedback)
    
    # Default response in case the graph doesn't yield any usable output
    ai_response_content = "I'm sorry, I couldn't find a good answer. Could you try rephrasing?"

    student_id = st.session_state.get("student_id", "unknown")

    # Collect trace info from LangSmith 
    with collect_runs() as cb:
        try:
            # Stream values emitted by the graph
            async for event in graph.astream(
                {"question": user_input,
                 "student_id": student_id}, 
                stream_mode="values", 
                config={"tags": ["streamlit_app_call"]}
                ):
                final_state = event # Update the final_state as receiving new events

            # Extract generated response if present in the final state
            if final_state and "generation" in final_state:
                 ai_response_content = final_state["generation"]
            else:
                 print(f"Final state missing 'generation': {final_state}") 

            # Extract LangSmith run ID for feedback tracking
            if cb.traced_runs:
                run_id = str(cb.traced_runs[-1].id) # LangSmith run ID will be created automatically
            else:
                 print("Warning: No runs traced by collect_runs.")

        except Exception as e:
            # On error, return fallback message and log the full exception
            ai_response_content = f"An error occurred while processing your request. Please check logs."
            traceback.print_exc() # Log full traceback for backend errors

    # Return both the response text and the tracing run ID
    return ai_response_content, run_id

# --- Display Chathistory with Optional Feedback ---

# A helper function to create a standardized feedback widget with consistent configuration.
def create_feedback_widget(feedback_key, run_id, client, disable_with_score=None):
    """
    Creates a standardized feedback widget with consistent configuration.

    Args:
        feedback_key (str): Unique key for the widget instance.
        run_id (str): Identifier for the current run.
        client (Any): Client object used for submitting feedback.
        disable_with_score (bool, optional): If True, disables widget when a score is present.

    Returns:
        Feedback widget instance rendered via streamlit_feedback.
    """

    # Return a pre-configured feedback widget
    return streamlit_feedback(
        feedback_type="thumbs",                     # "thumbs" allows thumbs-up/down input
        optional_text_label="Provide feedback",     # Encourages free-text feedback    
        key=feedback_key,
        on_submit=partial(submit_feedback, run_id=run_id, client=client), 
        kwargs={"run_id": run_id, "client": client}, # asses extra metadata to the feedback processor
        disable_with_score=disable_with_score, 
    )

# Chat Display and Feedback UI
# Loop over each message in the stored chat history (new format)
for i, message in enumerate(st.session_state.chat_history):
    role = message["role"]          # 'user' or 'ai'
    content = message["content"]    # Message text
    run_id = message.get("run_id")  # LangSmith run ID for this response (if any)

    # Use Streamlit's chat UI block to render the message
    with st.chat_message(role):
        st.markdown(content)

    # If this is an AI message and has a run ID, allow feedback as 👍👎 
    if role == "ai" and run_id:
        feedback_key = f"feedback_{i}" # Unique key per AI message

        # Initialize feedback state if not already present
        if feedback_key not in st.session_state:
            st.session_state[feedback_key] = None

        # Check if feedback has already been submitted (disable if so)
        current_feedback = st.session_state.get(feedback_key)
        score_to_disable_with = current_feedback.get("score") if current_feedback else None

        # Initialize client if needed and show thumbs-up/down feedback widget
        if client is None:
            client = init_langsmith_client()
        create_feedback_widget(feedback_key, run_id, client, score_to_disable_with)

    # Display warning only if run_id is missing for an AI message
    elif role == "ai" and not run_id:
         st.warning("Feedback not available for this message (missing run ID).", icon="⚠️")


# Initial greeting if chat history is empty
if not st.session_state.chat_history:
    with st.chat_message("ai"):
        st.write("Hello, I'm Clare-AI - TA Assistant. How can I help you today? 😊")

# User Input Processing
# Chat input
user_query = st.chat_input("Ask about Class info...")
# Process user input
if user_query is not None and user_query != "":
    st.session_state.chat_history.append({"role": "human", "content": user_query})

    # Display User Input
    with st.chat_message("human"):
        st.markdown(user_query)

    # AI Response Generation
    with st.chat_message("ai"):
        message_placeholder = st.empty()
        run_id = None 

        # Display Loading Indicator
        with message_placeholder.status("Consulting CGU databases..."):
            try:
                ai_response_content, run_id = asyncio.run(get_drucker_response_with_run_id(user_query))
            except Exception as e:
                 st.error(f"Error generating response: {e}")
                 print(f"Error in asyncio.run(get_drucker_response_with_run_id): {e}") # Debug
                 ai_response_content = "Sorry, I encountered an error generating the response."

        # Display AI Response
        message_placeholder.markdown(ai_response_content)

        # Add AI message *with* run_id to history before attempting to render feedback
        st.session_state.chat_history.append({"role": "ai", "content": ai_response_content, "run_id": run_id})

        # Find the most recent human-AI pair and insert into DB
        if len(st.session_state.chat_history) >= 2:
            last_human_msg = st.session_state.chat_history[-2]
            last_ai_msg = st.session_state.chat_history[-1]

            if last_human_msg["role"] == "human" and last_ai_msg["role"] == "ai":
                store_chat_to_db(st.session_state.get("student_id", "unknown"), last_human_msg["content"], last_ai_msg["content"])

        # Render feedback widget only if run_id was successfully obtained
        if run_id:
            new_message_index = len(st.session_state.chat_history) - 1
            feedback_key = f"feedback_{new_message_index}"

            if feedback_key not in st.session_state:
                 st.session_state[feedback_key] = None

            # Initialize client if needed and display feedback widget
            if client is None:
                client = init_langsmith_client()
            create_feedback_widget(feedback_key, run_id, client)
        
        # Display a warning if feedback is not possible becasue run_id is missing 
        elif not run_id:
             st.warning("Feedback not available for this message (missing run ID).", icon="⚠️")
             
    print("--- Finished Processing User Query ---") 