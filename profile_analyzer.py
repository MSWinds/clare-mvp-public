"""
Profile Analyzer - Evidence-based Learner Profile System
Refactored from summarizer.py to implement structured profile updates using evidence merging.
"""

import os
import uuid
import json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text, Table, Column, MetaData, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import asyncio

from profile_schemas import LearnerProfile, EvidenceItem, EvidenceCollection

# Load environment variables
load_dotenv()

# --- Environment Setup ---
connection_string = os.getenv("DB_CONNECTION")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not connection_string:
    raise ValueError("DB_CONNECTION environment variable not set.")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# Initialize database engine
engine = create_engine(connection_string)
metadata = MetaData()

# Updated table definition to match new JSON schema
student_profiles = Table(
    'student_profiles', metadata,
    Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('student_id', String, nullable=False, index=True),
    Column('profile_summary', JSONB, nullable=False, default={}),  # Changed to JSONB
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

# Initialize LLMs
llm_gpt = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=openai_api_key)
llm_mini = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=openai_api_key)

# Text Summary Generation Prompt for MVP
PROFILE_MERGE_SYSTEM_PROMPT = """You are an AI educational analyst creating personalized learner profiles for Clare-AI teaching assistant.

Your task is to analyze evidence about a student and generate a comprehensive text summary that will help Clare provide personalized teaching support.

Guidelines for creating the summary:

ANALYZE these key dimensions from the evidence:
1. **Basic Info**: Name, course enrollment, academic background
2. **Technical Profile**: Prior education, programming experience, AI tools familiarity  
3. **Cognitive Profile**: Comprehension ability, learning pace, reasoning style, execution ability
4. **Learning Style**: Preferred formats (visual, examples, hands-on), study patterns, motivation
5. **Challenges & Needs**: Knowledge gaps, pain points, misconceptions, support requirements
6. **AI Teaching Strategy**: Recommended feedback tone, guidance approach, intervention level

GENERATE a narrative summary that includes:
- Student's current technical level and background
- Learning style and cognitive patterns  
- Specific challenges and knowledge gaps
- Clear recommendations for the AI teaching assistant
- Suggested teaching approaches and tone

EXAMPLE of good summary format:
"The student is a [level] learner with [background]. They demonstrate [learning characteristics] and prefer [learning style]. Key challenges include [specific gaps]. 

Recommendations for the AI teaching assistant:
- [Specific teaching approach 1]
- [Specific teaching approach 2] 
- [Tone and interaction style]"

If current_profile already exists, UPDATE the summary by integrating new evidence while preserving established patterns. For weak/ambiguous evidence, maintain the existing summary.

Return ONLY a JSON object: {"text_summary": "your comprehensive summary here"}"""

# Evidence Extraction Prompt
EVIDENCE_EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["chat_history"],
    template="""Analyze this student-AI conversation from a Generative AI course and extract evidence for learner profiling.

Focus on extracting evidence for these dimensions:
- technical_profile: Python skills, AI tool experience, programming background
- cognitive_profile: Learning pace, comprehension style, reasoning patterns
- learning_style: Preferred formats, engagement patterns, motivation signals
- challenges_needs: Concept gaps, misconceptions, support requirements
- ai_strategy: Effective teaching approaches, feedback preferences

Extract only clear, observable evidence. Return a JSON array of evidence items.

Example format:
[
  {{
    "source": "interaction",
    "ts": "2025-09-03T10:00:00Z", 
    "dimension": "technical_profile",
    "field": "python_skill",
    "value": "beginner",
    "confidence": 0.8,
    "weight": 1.0,
    "note": "Student asked basic syntax questions"
  }}
]

Chat History:
{chat_history}

Return JSON array only:"""
)

# Define the state schema for the LangGraph workflow
class ProfileAnalysisState(TypedDict):
    """State for the profile analysis workflow."""
    student_id: str
    chat_history: str
    evidence_items: List[Dict[str, Any]]
    current_profile: Dict[str, Any]
    updated_profile: Dict[str, Any]
    analysis_type: str  # "interaction" or "weekly"

# Build the state graph
workflow = StateGraph(ProfileAnalysisState)

# --- Workflow Node Functions ---

async def fetch_chat_history(state: ProfileAnalysisState) -> Dict[str, Any]:
    """Fetch recent chat history for evidence extraction."""
    student_id = state.get("student_id")
    analysis_type = state.get("analysis_type", "interaction")
    
    # Adjust history limit based on analysis type
    history_limit = 5 if analysis_type == "interaction" else 20
    
    print(f"Node 'fetch_chat_history': Fetching {history_limit} entries for {student_id}")
    
    if not student_id:
        return {"chat_history": "Error: student_id missing."}
    
    query = text("""
        SELECT user_input, ai_response, timestamp
        FROM chat_history
        WHERE student_id = :student_id
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"student_id": student_id, "limit": history_limit}).fetchall()
        
        if not rows:
            return {"chat_history": "No prior interactions found."}
        
        chat_lines = []
        for user_input, ai_resp, ts in reversed(rows):
            user_input_str = user_input or "[No input]"
            ai_resp_str = ai_resp or "[No response]"
            ts_str = ts.strftime('%Y-%m-%d %H:%M:%S') if ts else "[No timestamp]"
            chat_lines.append(f"[{ts_str}] Student: {user_input_str}")
            chat_lines.append(f"[{ts_str}] AI: {ai_resp_str}")
        
        chat_history = "\n".join(chat_lines)
        print(f"Fetched {len(rows)} chat history entries.")
        return {"chat_history": chat_history}
        
    except Exception as e:
        print(f"Database error fetching history: {e}")
        return {"chat_history": f"Error fetching history: {e}"}

async def extract_evidence(state: ProfileAnalysisState) -> Dict[str, Any]:
    """Extract evidence items from chat history using LLM."""
    chat_history = state.get("chat_history", "")
    
    print("Node 'extract_evidence': Analyzing chat for evidence")
    
    if not chat_history or "No prior interactions" in chat_history:
        return {"evidence_items": []}
    
    try:
        # Use mini model for evidence extraction (faster, cheaper)
        messages = [
            SystemMessage(content="Extract learner profiling evidence from student conversations."),
            HumanMessage(content=EVIDENCE_EXTRACTION_PROMPT.format(chat_history=chat_history))
        ]
        
        response = await llm_mini.ainvoke(messages)
        evidence_json = response.content.strip()
        
        # Parse JSON response
        evidence_items = json.loads(evidence_json)
        
        # Validate evidence items
        validated_evidence = []
        for item in evidence_items:
            try:
                evidence_item = EvidenceItem(**item)
                validated_evidence.append(evidence_item.model_dump())
            except Exception as validation_error:
                print(f"Invalid evidence item skipped: {validation_error}")
                continue
        
        print(f"Extracted {len(validated_evidence)} valid evidence items.")
        return {"evidence_items": validated_evidence}
        
    except Exception as e:
        print(f"Error extracting evidence: {e}")
        return {"evidence_items": []}

async def fetch_current_profile(state: ProfileAnalysisState) -> Dict[str, Any]:
    """Fetch current learner profile from database."""
    student_id = state.get("student_id")
    
    print(f"Node 'fetch_current_profile': Getting profile for {student_id}")
    
    if not student_id:
        return {"current_profile": {}}
    
    query = text("""
        SELECT profile_summary, timestamp
        FROM student_profiles
        WHERE student_id = :student_id
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"student_id": student_id}).fetchone()
        
        if not result or not result.profile_summary:
            return {"current_profile": {}}
        
        # Handle both new JSON format and legacy text format
        profile_data = result.profile_summary
        if isinstance(profile_data, str):
            # Legacy text format - wrap in legacy structure
            current_profile = {"legacy_profile": profile_data}
        else:
            # New JSON format
            current_profile = profile_data
        
        print("Retrieved current profile from database.")
        return {"current_profile": current_profile}
        
    except Exception as e:
        print(f"Error fetching current profile: {e}")
        return {"current_profile": {}}

async def merge_profile_with_evidence(state: ProfileAnalysisState) -> Dict[str, Any]:
    """Merge evidence into current profile using LLM to generate text summary."""
    current_profile = state.get("current_profile", {})
    evidence_items = state.get("evidence_items", [])
    
    print("Node 'merge_profile_with_evidence': Merging evidence with profile")
    
    if not evidence_items:
        print("No evidence to merge - returning current profile unchanged.")
        return {"updated_profile": current_profile}
    
    try:
        # Extract current text summary if exists
        current_summary = current_profile.get("text_summary", "") if current_profile else ""
        
        # Prepare the merge prompt for text summary generation
        user_prompt = f"""current_profile = {{"text_summary": "{current_summary}"}}
evidence = {json.dumps(evidence_items, indent=2)}"""
        
        messages = [
            SystemMessage(content=PROFILE_MERGE_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        
        # Use main GPT model for critical merge logic
        response = await llm_gpt.ainvoke(messages)
        
        # Parse the response - should be {"text_summary": "..."}
        try:
            updated_profile = json.loads(response.content.strip())
            if "text_summary" not in updated_profile:
                # Fallback if LLM didn't follow format
                updated_profile = {"text_summary": response.content.strip()}
        except json.JSONDecodeError:
            # Fallback if response isn't valid JSON
            updated_profile = {"text_summary": response.content.strip()}
        
        print("Profile merge completed successfully.")
        return {"updated_profile": updated_profile}
        
    except Exception as e:
        print(f"Error during profile merge: {e}")
        return {"updated_profile": current_profile}

async def save_updated_profile(state: ProfileAnalysisState) -> Dict[str, Any]:
    """Save the updated profile to database using UPSERT (one record per student)."""
    student_id = state.get("student_id")
    updated_profile = state.get("updated_profile", {})
    
    print(f"Node 'save_updated_profile': Saving profile for {student_id}")
    
    if not student_id or not updated_profile:
        print("Missing student_id or updated_profile - skipping save.")
        return {}
    
    try:
        # Ensure text_summary format for MVP
        if "text_summary" in updated_profile:
            complete_profile = updated_profile  # Already in correct format
        else:
            # Fallback if profile doesn't have text_summary
            complete_profile = {"text_summary": "Profile data available but not in text summary format."}
        
        # UPSERT: Insert or update existing record (one record per student_id)
        upsert_stmt = text("""
            INSERT INTO student_profiles (id, student_id, profile_summary, timestamp)
            VALUES (:id, :student_id, :profile_summary, :timestamp)
            ON CONFLICT (student_id) DO UPDATE SET
                profile_summary = EXCLUDED.profile_summary,
                timestamp = EXCLUDED.timestamp
        """)
        
        with engine.begin() as conn:
            conn.execute(upsert_stmt, {
                "id": uuid.uuid4(),
                "student_id": student_id,
                "profile_summary": complete_profile,  # SQLAlchemy handles JSONB conversion
                "timestamp": datetime.now(timezone.utc)
            })
        
        print(f"Updated profile saved to database for {student_id}")
        return {"save_status": "success"}
        
    except Exception as e:
        print(f"Error saving updated profile: {e}")
        return {"save_status": "failed"}

# --- Build the workflow graph ---
workflow.add_node("fetch_chat_history", fetch_chat_history)
workflow.add_node("extract_evidence", extract_evidence)
workflow.add_node("fetch_current_profile", fetch_current_profile)
workflow.add_node("merge_profile_with_evidence", merge_profile_with_evidence)
workflow.add_node("save_updated_profile", save_updated_profile)

# Set entry point and define the flow
workflow.set_entry_point("fetch_chat_history")
workflow.add_edge("fetch_chat_history", "extract_evidence")
workflow.add_edge("extract_evidence", "fetch_current_profile")
workflow.add_edge("fetch_current_profile", "merge_profile_with_evidence")
workflow.add_edge("merge_profile_with_evidence", "save_updated_profile")
workflow.add_edge("save_updated_profile", END)

# Compile the workflow
app = workflow.compile()

# --- Main API Functions ---

async def analyze_and_update_profile(student_id: str, analysis_type: str = "interaction") -> Dict[str, Any]:
    """
    Main entry point for profile analysis and updates.
    
    Args:
        student_id: The student's unique identifier
        analysis_type: "interaction" (recent chats) or "weekly" (broader analysis)
    
    Returns:
        Dictionary with analysis results and updated profile
    """
    print(f"\n--- Starting profile analysis for {student_id} ({analysis_type}) ---")
    
    initial_state = {
        "student_id": student_id,
        "analysis_type": analysis_type
    }
    
    try:
        final_state = await app.ainvoke(initial_state)
        
        result = {
            "student_id": student_id,
            "analysis_type": analysis_type,
            "evidence_count": len(final_state.get("evidence_items", [])),
            "updated_profile": final_state.get("updated_profile", {}),
            "save_status": final_state.get("save_status", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"--- Profile analysis completed for {student_id} ---")
        return result
        
    except Exception as e:
        print(f"Profile analysis failed for {student_id}: {e}")
        return {
            "student_id": student_id,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def extract_evidence_from_recent_history(student_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Extract evidence from recent chat history without full profile update.
    Useful for integration with main workflow.
    """
    query = text("""
        SELECT user_input, ai_response, timestamp
        FROM chat_history
        WHERE student_id = :student_id
        ORDER BY timestamp DESC
        LIMIT :limit
    """)
    
    try:
        with engine.connect() as conn:
            rows = conn.execute(query, {"student_id": student_id, "limit": limit}).fetchall()
        
        if not rows:
            return []
        
        # Build chat history string
        chat_lines = []
        for user_input, ai_resp, ts in reversed(rows):
            chat_lines.append(f"Student: {user_input or '[No input]'}")
            chat_lines.append(f"AI: {ai_resp or '[No response]'}")
        
        chat_history = "\n".join(chat_lines)
        
        # Extract evidence using LLM
        messages = [
            SystemMessage(content="Extract learner profiling evidence from student conversations."),
            HumanMessage(content=EVIDENCE_EXTRACTION_PROMPT.format(chat_history=chat_history))
        ]
        
        response = await llm_mini.ainvoke(messages)
        evidence_items = json.loads(response.content.strip())
        
        return evidence_items
        
    except Exception as e:
        print(f"Error extracting evidence: {e}")
        return []

def get_structured_profile(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent profile for a student (text summary format for MVP).
    Synchronous function for easy integration with existing code.
    """
    query = text("""
        SELECT profile_summary, timestamp
        FROM student_profiles
        WHERE student_id = :student_id
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"student_id": student_id}).fetchone()
        
        if result and result.profile_summary:
            return result.profile_summary  # Should be {"text_summary": "..."}
        return None
        
    except Exception as e:
        print(f"Error retrieving profile: {e}")
        return None

def get_profile_text_summary(student_id: str) -> Optional[str]:
    """
    Get just the text summary for a student (for direct use in answer generator).
    """
    profile = get_structured_profile(student_id)
    if profile and "text_summary" in profile:
        return profile["text_summary"]
    return None

# --- Testing and CLI Interface ---
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_student_id = sys.argv[1]
        analysis_type = sys.argv[2] if len(sys.argv) > 2 else "interaction"
    else:
        test_student_id = "123456"
        analysis_type = "interaction"
    
    print(f"Testing profile analyzer with student ID: {test_student_id}")
    
    # Run the profile analysis
    result = asyncio.run(analyze_and_update_profile(test_student_id, analysis_type))
    
    print("\n--- Analysis Result ---")
    print(json.dumps(result, indent=2, default=str))