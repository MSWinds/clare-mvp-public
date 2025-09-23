import os
import uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text, Table, Column, MetaData, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from ..prompts.summarizer_prompts import gen_profile_prompt
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from typing import TypedDict
import asyncio

connection_string = os.getenv("DATABASE_URL")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not connection_string:
    raise ValueError("DATABASE_URL environment variable not set.")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

engine = create_engine(connection_string)
metadata = MetaData()

student_profiles = Table(
    'student_profiles', metadata,
    Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('student_id', String, nullable=False, index=True),
    Column('profile_summary', String, nullable=False),
    Column('student_name', String(255), nullable=True),
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

try:
    print("Creating tables if they don\'t exist...")
    metadata.create_all(engine)
    print("Tables checked/created.")
except Exception as e:
    print(f"Error creating tables: {e}")

llm_gpt = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=openai_api_key
)

class StudentProfileState(TypedDict):
    """Represents the state of the student profiling graph."""
    student_id: str
    chat_history: str
    profile_summary: str

graph = StateGraph(StudentProfileState)

async def fetch_history(state: StudentProfileState) -> dict:
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

async def summarize_and_save(state: StudentProfileState) -> dict:
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
        try:
            messages = [
                SystemMessage(content="Generate student profile summary for generative AI course."),
                HumanMessage(content=gen_profile_prompt.format(chat_history=chat_history))
            ]
            response = await llm_gpt.ainvoke(input=messages)
            content = response.content
            if isinstance(content, list):
                profile = "".join(part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text")
            else:
                profile = str(content)
            print("Profile summary generated successfully.")
        except Exception as e:
            print(f"Error calling LLM for {student_id}: {e}")
            profile = f"Error generating profile summary for student ID {student_id}: {e}\n\nChat history used:\n{chat_history}"

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

graph.add_node("fetch_history", fetch_history)
graph.add_node("summarize_and_save", summarize_and_save)

graph.set_entry_point("fetch_history")

graph.add_edge("fetch_history", "summarize_and_save")
graph.add_edge("summarize_and_save", END)

app = graph.compile()

async def create_student_profile(student_id: str) -> str:
    print(f"\n--- Starting profile generation for student ID: {student_id} ---")
    initial_state = {"student_id": student_id}
    try:
        final_state = await app.ainvoke(initial_state)
        profile = final_state.get("profile_summary", "Profile generation completed but summary not found in final state.")
        print(f"--- Profile generation finished for student ID: {student_id} ---")
        return profile
    except Exception as e:
        print(f"An unexpected error occurred during graph execution for {student_id}: {e}")
        return f"Profile generation failed due to an unexpected error: {e}"

if __name__ == "__main__":
    test_student_id = "123456"
    generated_profile = asyncio.run(create_student_profile(test_student_id))
    print("\n--- Generated Student Profile Summary ---")
    print(generated_profile)
