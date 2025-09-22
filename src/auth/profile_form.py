"""
Student Profile Form Module
Handles the questionnaire for new users and profile editing.
"""

import streamlit as st
import json
from datetime import datetime, timezone
from typing import Dict, Any

def convert_questionnaire_to_evidence(profile_data: Dict[str, Any]) -> list:
    """Convert UI questionnaire responses to evidence items for profile_analyzer"""
    evidence_items = []
    current_time = datetime.now().isoformat() + "Z"

    # Basic Information
    if profile_data.get("name"):
        evidence_items.append({
            "field": "name",
            "value": json.dumps(profile_data["name"]) if isinstance(profile_data["name"], (dict, list)) else profile_data["name"],
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q1: Student name"
        })

    if profile_data.get("course"):
        evidence_items.append({
            "field": "course_context",
            "value": json.dumps({"course": profile_data["course"]}) if profile_data["course"] else "{}",
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q2: Course enrollment"
        })

    # Academic Background
    if profile_data.get("academic_background"):
        evidence_items.append({
            "field": "academic_background",
            "value": profile_data["academic_background"],
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q3: Academic background"
        })

    # Programming Experience
    if profile_data.get("programming_experience"):
        programming_value = json.dumps(profile_data["programming_experience"]) if isinstance(profile_data["programming_experience"], list) else profile_data["programming_experience"]
        evidence_items.append({
            "field": "technical_skills",
            "value": programming_value,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q4: Programming experience"
        })

    # Technology Familiarity
    if profile_data.get("tech_familiarity"):
        tech_value = json.dumps(profile_data["tech_familiarity"]) if isinstance(profile_data["tech_familiarity"], list) else profile_data["tech_familiarity"]
        evidence_items.append({
            "field": "tech_familiarity",
            "value": tech_value,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q5: Technology familiarity"
        })

    # Study Hours (convert to study intensity)
    if profile_data.get("study_hours"):
        evidence_items.append({
            "field": "study_intensity",
            "value": "intensive" if "More than 20" in profile_data["study_hours"] else
                     "moderate" if "10–20" in profile_data["study_hours"] else "relaxed",
            "source": "questionnaire",
            "timestamp": current_time,
            "note": f"Q14: {profile_data['study_hours']} study hours per week"
        })

    # Learning Style
    if profile_data.get("learning_style"):
        evidence_items.append({
            "field": "learning_preferences",
            "value": json.dumps([profile_data["learning_style"].lower()]),
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q15: Preferred learning style"
        })

    # Learning Goals
    if profile_data.get("learning_goals"):
        goals_value = json.dumps(profile_data["learning_goals"]) if isinstance(profile_data["learning_goals"], list) else profile_data["learning_goals"]
        evidence_items.append({
            "field": "learning_goals",
            "value": goals_value,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q16: Learning goals"
        })

    # Motivation
    if profile_data.get("motivation"):
        evidence_items.append({
            "field": "motivation",
            "value": profile_data["motivation"].lower().replace(" ", "_"),
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q17: Primary motivation"
        })

    # Learning Challenges
    if profile_data.get("learning_challenges"):
        evidence_items.append({
            "field": "learning_challenges",
            "value": json.dumps([profile_data["learning_challenges"]]),
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q18: Learning challenges"
        })

    # AI Support Preferences
    if profile_data.get("ai_support"):
        support_value = json.dumps(profile_data["ai_support"]) if isinstance(profile_data["ai_support"], list) else profile_data["ai_support"]
        evidence_items.append({
            "field": "support_preferences",
            "value": support_value,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q19: AI support preferences"
        })

    # Personality (convert to guidance mode)
    if profile_data.get("personality"):
        guidance_mode = "encouraging" if profile_data["personality"] == "Introverted" else "collaborative"
        evidence_items.append({
            "field": "guidance_mode",
            "value": guidance_mode,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": f"Q21: {profile_data['personality']} personality"
        })

    # Clare Motivation
    if profile_data.get("clare_motivation"):
        motivation_value = json.dumps(profile_data["clare_motivation"]) if isinstance(profile_data["clare_motivation"], list) else profile_data["clare_motivation"]
        evidence_items.append({
            "field": "clare_motivation",
            "value": motivation_value,
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q22: Clare motivation"
        })

    # Industry Interest
    if profile_data.get("industry_interest"):
        evidence_items.append({
            "field": "industry_interest",
            "value": json.dumps([profile_data["industry_interest"]]),
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q23: Industry interest"
        })

    # Career Goal
    if profile_data.get("career_goal"):
        evidence_items.append({
            "field": "career_goals",
            "value": json.dumps([profile_data["career_goal"]]),
            "source": "questionnaire",
            "timestamp": current_time,
            "note": "Q24: Career goal"
        })

    return evidence_items

def process_questionnaire_with_profile_analyzer(profile_data: Dict[str, Any]):
    """Process questionnaire through profile_analyzer and store in database"""
    try:
        from src.workflows.profile_analyzer import analyze_and_update_profile

        student_id = profile_data["student_id"]
        evidence_items = convert_questionnaire_to_evidence(profile_data)

        print(f"🚀 Started questionnaire processing for {profile_data['student_id']}")

        # Run the profile analysis asynchronously
        import asyncio
        result = asyncio.run(analyze_and_update_profile(student_id, "questionnaire"))

        return {
            "success": True,
            "message": "Profile analysis completed successfully",
            "result": result
        }

    except Exception as e:
        print(f"Questionnaire processing error: {e}")
        return {
            "success": False,
            "message": f"Profile processing failed: {str(e)}",
            "save_status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

def show_profile_form(is_update: bool = False):
    """Display the student profile questionnaire form"""

    # Get existing profile data for editing
    existing_data = st.session_state.get("profile_data", {}) or {}

    with st.form("student_profile_form"):
        if is_update:
            st.header("✏️ Update Your Learning Profile")
            st.markdown("Update any information below and save your changes")
        else:
            st.header("🎓 Welcome! Let's personalize your learning with Clare")
            st.markdown("Tell us a bit about yourself so Clare can support your study journey")

        # Part 1: Basic Information (Required)
        st.subheader("📝 Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            student_name = st.text_input(
                "What's your name?",
                value=existing_data.get("name", ""),
                placeholder="Enter your full name"
            )

        with col2:
            student_id = st.text_input(
                "Student ID",
                value=existing_data.get("student_id", ""),
                placeholder="Enter your student ID"
            )

        course = st.selectbox(
            "Which course are you taking?",
            ["IST 345.1 - Building Generative AI Applications", "Other"],
            index=0 if existing_data.get("course") == "IST 345.1 - Building Generative AI Applications" else 1
        )

        # Part 2: Academic Background
        st.subheader("🎓 Academic Background")
        academic_background = st.selectbox(
            "What's your academic background?",
            [
                "Computer Science/Information Technology",
                "Engineering",
                "Business/Management",
                "Social Sciences",
                "Natural Sciences",
                "Liberal Arts",
                "Other"
            ],
            index=0 if not existing_data.get("academic_background") else None
        )

        programming_experience = st.selectbox(
            "Programming Experience",
            [
                "Beginner (little to no experience)",
                "Intermediate (some courses/projects)",
                "Advanced (extensive experience)",
                "Expert (professional developer)"
            ],
            index=0 if not existing_data.get("programming_experience") else None
        )

        tech_familiarity = st.multiselect(
            "Which technologies are you familiar with?",
            [
                "Python",
                "JavaScript",
                "Java",
                "C++",
                "SQL",
                "HTML/CSS",
                "Git/GitHub",
                "APIs",
                "Machine Learning",
                "Data Science",
                "Cloud Computing",
                "None of the above"
            ],
            default=existing_data.get("tech_familiarity", [])
        )

        # Part 3: Learning Preferences
        st.subheader("📚 Learning Preferences")

        study_hours = st.selectbox(
            "How many hours per week do you typically study?",
            [
                "Less than 5 hours",
                "5–10 hours",
                "10–20 hours",
                "More than 20 hours"
            ],
            index=0 if not existing_data.get("study_hours") else None
        )

        learning_style = st.selectbox(
            "What's your preferred learning style?",
            [
                "Visual (diagrams, charts)",
                "Auditory (lectures, discussions)",
                "Kinesthetic (hands-on practice)",
                "Reading/Writing (text-based)"
            ],
            index=0 if not existing_data.get("learning_style") else None
        )

        learning_goals = st.multiselect(
            "What are your learning goals for this course?",
            [
                "Build practical AI applications",
                "Understand AI fundamentals",
                "Career advancement",
                "Academic requirements",
                "Personal interest",
                "Research purposes"
            ],
            default=existing_data.get("learning_goals", [])
        )

        # Part 4: Motivation & Challenges
        st.subheader("🎯 Motivation & Challenges")

        motivation = st.selectbox(
            "What motivates you most in learning?",
            [
                "Practical applications",
                "Theoretical understanding",
                "Problem solving",
                "Career opportunities",
                "Personal growth"
            ],
            index=0 if not existing_data.get("motivation") else None
        )

        learning_challenges = st.selectbox(
            "What's your biggest learning challenge?",
            [
                "Time management",
                "Complex concepts",
                "Technical implementation",
                "Staying motivated",
                "Finding relevant resources"
            ],
            index=0 if not existing_data.get("learning_challenges") else None
        )

        ai_support = st.multiselect(
            "How would you like AI to support your learning?",
            [
                "Explain concepts clearly",
                "Provide practice exercises",
                "Give step-by-step guidance",
                "Answer specific questions",
                "Suggest additional resources",
                "Track my progress"
            ],
            default=existing_data.get("ai_support", [])
        )

        # Part 5: Personal Preferences
        st.subheader("👤 Personal Preferences")

        personality = st.selectbox(
            "How would you describe your personality?",
            ["Extroverted", "Introverted", "Ambivert"],
            index=0 if not existing_data.get("personality") else None
        )

        clare_motivation = st.multiselect(
            "What would motivate you to use Clare-AI regularly?",
            [
                "Quick answers to questions",
                "Personalized learning path",
                "Interactive problem solving",
                "Progress tracking",
                "Study reminders",
                "Peer collaboration features"
            ],
            default=existing_data.get("clare_motivation", [])
        )

        # Part 6: Future Goals
        st.subheader("🚀 Future Goals")

        industry_interest = st.selectbox(
            "Which industry interests you most?",
            [
                "Technology/Software",
                "Healthcare",
                "Finance",
                "Education",
                "Research/Academia",
                "Consulting",
                "Entrepreneurship",
                "Other"
            ],
            index=0 if not existing_data.get("industry_interest") else None
        )

        career_goal = st.selectbox(
            "What's your primary career goal?",
            [
                "AI/ML Engineer",
                "Data Scientist",
                "Software Developer",
                "Product Manager",
                "Researcher",
                "Consultant",
                "Entrepreneur",
                "Other"
            ],
            index=0 if not existing_data.get("career_goal") else None
        )

        # Form submission buttons
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            submit_button = st.form_submit_button("💾 Save Profile", type="primary")

        with col2:
            cancel_button = st.form_submit_button("❌ Cancel")

        with col3:
            if existing_data:  # Only show clear button if there's existing data
                clear_button = st.form_submit_button("🗑️ Clear Profile")

        # Handle form submission
        if submit_button:
            if not student_name.strip() or not student_id.strip():
                st.error("⚠️ Name and Student ID are required!")
            else:
                # Create profile data dictionary
                profile_data = {
                    "student_id": student_id.strip(),
                    "name": student_name.strip(),
                    "course": course,
                    "academic_background": academic_background,
                    "programming_experience": programming_experience,
                    "tech_familiarity": tech_familiarity,
                    "study_hours": study_hours,
                    "learning_style": learning_style,
                    "learning_goals": learning_goals,
                    "motivation": motivation,
                    "learning_challenges": learning_challenges,
                    "ai_support": ai_support,
                    "personality": personality,
                    "clare_motivation": clare_motivation,
                    "industry_interest": industry_interest,
                    "career_goal": career_goal
                }

                st.session_state["profile_data"] = profile_data
                st.session_state["student_id"] = student_id.strip()
                st.session_state["show_profile_form"] = False

                # Process questionnaire through profile_analyzer and store in database
                try:
                    process_questionnaire_with_profile_analyzer(profile_data)
                    st.success("✅ Profile saved and processing started!")
                    st.info("🔄 Your learning profile is being created in the background...")

                    # Mark profile as complete for new users
                    if not is_update:
                        from src.database.config import mark_profile_complete
                        mark_profile_complete(student_id.strip())

                except Exception as e:
                    st.error(f"⚠️ Profile saved to session, but processing failed: {e}")
                    print(f"Questionnaire processing error: {e}")

                st.rerun()

        elif cancel_button:
            st.session_state["show_profile_form"] = False
            st.rerun()

        elif 'clear_button' in locals() and clear_button:
            st.session_state["profile_data"] = None
            st.session_state["student_id"] = ""
            st.session_state["show_profile_form"] = False
            st.warning("🗑️ Profile cleared!")
            st.rerun()