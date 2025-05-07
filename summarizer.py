import os
import uuid
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text, Table, Column, MetaData, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from typing import TypedDict
import asyncio # Import asyncio

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

# Define a table to store student profile summaries
student_profiles = Table(
    'student_profiles', metadata,
    Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('student_id', String, nullable=False, index=True),
    Column('profile_summary', String, nullable=False),
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

# Create tables if they don't exist
try:
    print("Creating tables if they don't exist...")
    metadata.create_all(engine)
    print("Tables checked/created.")
except Exception as e:
    print(f"Error creating tables: {e}")

# Initialize LLM
llm_gpt = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=openai_api_key)

# Prompt template for profiling
gen_profile_prompt = PromptTemplate(
    input_variables=["chat_history"],
    template=(
        "You are an educational analyst creating a student profile."
        "Based on the following chat history between a student and an AI about a generative AI course, "
        "generate a comprehensive student profile summary. Focus on:\n"
        "- Student's overall understanding level.\n"
        "- Key concepts they grasped or struggled with.\n"
        "- Specific questions or topics they focused on.\n"
        "- Potential strengths and areas for improvement.\n"
        "- Actionable learning recommendations (e.g., topics to review, exercises to try).\n\n"
        "Format the summary clearly with headings for each section.\n\n"
        "Chat History:\n{chat_history}"
    )
)

# Define the state schema for the graph using TypedDict
class StudentProfileState(TypedDict):
    """Represents the state of the student profiling graph."""
    student_id: str
    chat_history: str
    profile_summary: str

# Build the state graph
graph = StateGraph(StudentProfileState)


# --- Define the node functions to return state updates (dictionaries) ---

# Node to fetch history
async def fetch_history(state: StudentProfileState) -> dict:
    """Fetches recent chat history for the student from the database and returns state update."""
    student_id = state.get("student_id")
    print(f"Node 'fetch_history': Fetching history for student ID: {student_id}")

    chat_history_content = "Error: student_id missing."
    if not student_id:
        print("Error in 'fetch_history': student_id is missing from state.")
    else:
        history_limit = 10
        query = text("""
            SELECT user_input, ai_response, timestamp
            FROM chat_history
            WHERE student_id = :student_id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)

        chat_lines = []
        try:
            with engine.connect() as conn:
                rows = conn.execute(query, {"student_id": student_id, "limit": history_limit}).fetchall()

            if not rows:
                print(f"No chat history found for student ID: {student_id}")
                chat_history_content = "No prior interactions found."
            else:
                for user_input, ai_resp, ts in reversed(rows):
                    user_input_str = user_input if user_input is not None else "[No input]"
                    ai_resp_str = ai_resp if ai_resp is not None else "[No response]"
                    ts_str = ts.strftime('%Y-%m-%d %H:%M:%S') if ts else "[No timestamp]"
                    chat_lines.append(f"[{ts_str}] Student: {user_input_str}")
                    chat_lines.append(f"[{ts_str}] AI: {ai_resp_str}")
                chat_history_content = "\n".join(chat_lines)
                print(f"Fetched {len(rows)} history entries.")

        except Exception as e:
            print(f"Database error fetching history for {student_id}: {e}")
            chat_history_content = f"Error fetching history: {e}"
            pass

    return {"chat_history": chat_history_content}


# Node to summarize and save
async def summarize_and_save(state: StudentProfileState) -> dict:
    """Generates profile summary using LLM, stores it, and returns state update."""
    student_id = state.get("student_id")
    chat_history = state.get("chat_history", "")
    print(f"Node 'summarize_and_save': Summarizing and saving for student ID: {student_id}")

    profile = "Profile generation failed: student_id missing or no history."
    if not student_id:
        print("Error in 'summarize_and_save': student_id is missing from state.")
    elif not chat_history or "No prior interactions found." in chat_history or "Error fetching history" in chat_history:
         print(f"No valid chat history for {student_id}, generating a default message.")
         profile = chat_history
    else:
        # Call LLM to generate profile summary using ainvoke
        try:
            messages = [
                SystemMessage(content="Generate student profile summary for generative AI course."),
                HumanMessage(content=gen_profile_prompt.format(chat_history=chat_history))
            ]
            # Use ainvoke for async prediction and await it
            response = await llm_gpt.ainvoke(input=messages)
            profile = response.content
            print("Profile summary generated successfully.")
        except Exception as e:
            print(f"Error calling LLM for {student_id}: {e}")
            profile = f"Error generating profile summary for student ID {student_id}: {e}\n\nChat history used:\n{chat_history}"

    # Store summary into database (This happens regardless of LLM success if student_id exists)
    if student_id:
        try:
            insert_stmt = student_profiles.insert().values(
                id=uuid.uuid4(),
                student_id=student_id,
                profile_summary=profile,
                timestamp=datetime.now(timezone.utc)
            )
            with engine.begin() as conn:
                conn.execute(insert_stmt)
            print(f"Profile summary saved to DB for student ID: {student_id}")
        except Exception as e:
            print(f"Database error saving profile for {student_id}: {e}")
            profile = f"Profile saved with DB error: {e}\n\n" + profile
            pass

    return {"profile_summary": profile}


# --- Add nodes to the graph ---
graph.add_node("fetch_history", fetch_history)
graph.add_node("summarize_and_save", summarize_and_save)

# Set the entry point
graph.set_entry_point("fetch_history")

# Add edges (transitions between nodes)
graph.add_edge("fetch_history", "summarize_and_save")
graph.add_edge("summarize_and_save", END)


# Compile the graph
app = graph.compile()

# --- Make the entry point function async and await the graph invocation ---
async def create_student_profile(student_id: str) -> str:
    """
    Runs the LangGraph agent (async) to generate a student profile summary
    from chat history and store it in the database.

    Args:
        student_id: The unique identifier for the student.

    Returns:
        The generated profile summary string, or an error message.
    """
    print(f"\n--- Starting profile generation for student ID: {student_id} ---")
    initial_state = {"student_id": student_id}
    try:
        # Invoke the compiled graph asynchronously and await the result
        final_state = await app.ainvoke(initial_state)
        profile = final_state.get("profile_summary", "Profile generation completed but summary not found in final state.")
        print(f"--- Profile generation finished for student ID: {student_id} ---")
        return profile
    except Exception as e:
        print(f"An unexpected error occurred during graph execution for {student_id}: {e}")
        return f"Profile generation failed due to an unexpected error: {e}"

# --- Use asyncio.run() to execute the top-level async function ---
if __name__ == "__main__":
    test_student_id = "123456"

    # --- Optional: Add dummy data for testing if chat_history is empty ---
    # from datetime import timedelta # Already imported
    # try:
    #     with engine.begin() as conn:
    #         # Add dummy data for test_student_id
    #         conn.execute(text("""
    #             INSERT INTO chat_history (id, student_id, user_input, ai_response, timestamp)
    #             VALUES (:id, :sid, :ui, :ai, :ts)
    #         """),
    #         [
    #             {"id": uuid.uuid4(), "sid": test_student_id, "ui": "What is a large language model?", "ai": "It's an AI trained on vast text data to understand and generate human-like text.", "ts": datetime.now(timezone.utc) - timedelta(hours=2)},
    #             {"id": uuid.uuid4(), "sid": test_student_id, "ui": "How do they learn?", "ai": "They learn patterns, grammar, facts, and reasoning by predicting the next word in a sentence.", "ts": datetime.now(timezone.utc) - timedelta(hours=1)},
    #             {"id": uuid.uuid4(), "sid": test_student_id, "ui": "Can they access the internet?", "ai": "Typically, base LLMs don't have real-time internet access, but they can be augmented with search tools.", "ts": datetime.now(timezone.utc) - timedelta(minutes=30)},
    #         ])
    #         print(f"Added dummy chat history for student ID: {test_student_id}")
    # except Exception as e:
    #     print(f"Could not add dummy chat history (is chat_history table created? Check DB_CONNECTION): {e}")
    # --- End Optional Dummy Data Block ---

    # Use asyncio.run() to execute the top-level async function
    generated_profile = asyncio.run(create_student_profile(test_student_id))

    print("\n--- Generated Student Profile Summary ---")
    print(generated_profile)

    # Optional: Verify the profile was saved in the database (needs to be async if querying in async function)
    # If you want to verify asynchronously after the run, you'd need another async function
    # and run that as well, or do synchronous verification here if your DB library supports it
    # synchronously. SQLAlchemy usually works fine synchronously outside the graph nodes.
    # try:
    #     print("\n--- Verifying saved profile in DB ---")
    #     query_check = text("SELECT profile_summary, timestamp FROM student_profiles WHERE student_id = :sid ORDER BY timestamp DESC LIMIT 1")
    #     with engine.connect() as conn:
    #         latest_profile = conn.execute(query_check, {"sid": test_student_id}).fetchone()
    #     if latest_profile:
    #         print("Found latest profile in DB:")
    #         print(f"Timestamp: {latest_profile.timestamp}")
    #         print(f"Summary (first 200 chars): {latest_profile.profile_summary[:200]}...")
    #     else:
    #          print("No profile found in DB for this student ID.")
    # except Exception as e:
    #     print(f"Error verifying profile in DB: {e}")