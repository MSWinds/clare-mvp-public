"""
Database Configuration Module
Centralizes all database connections, environment variables, and table definitions.
"""

import os
from sqlalchemy import create_engine, Table, Column, String, Text, MetaData, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from datetime import datetime, timezone
import uuid

# Load environment variables (only for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available in production (Streamlit Cloud)
    pass

# Environment Variables
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

# Validate required environment variables
def validate_env_vars():
    """Validate that all required environment variables are set."""
    required_vars = {
        "DATABASE_URL": DATABASE_URL,
        "OPENAI_API_KEY": OPENAI_API_KEY,
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    return True

# Database Engine (lazy initialization)
_engine = None

def get_database_engine():
    """Get database engine with lazy initialization."""
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set.")
        _engine = create_engine(DATABASE_URL)
    return _engine

# Table Definitions
metadata = MetaData()

# Chat History Table
chat_history_table = Table(
    'chat_history', metadata,
    Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('student_id', Text, nullable=False),
    Column('user_input', Text, nullable=False),
    Column('ai_response', Text, nullable=False),
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

# Student Profiles Table
student_profiles_table = Table(
    'student_profiles', metadata,
    Column('id', PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column('student_id', String, nullable=False, index=True),
    Column('profile_summary', JSONB, nullable=False, default={}),
    Column('is_profile_complete', Boolean, nullable=False, default=False),
    Column('last_login', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('profile_version', Integer, nullable=False, default=1),
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

def create_tables():
    """Create all tables if they don't exist."""
    engine = get_database_engine()
    metadata.create_all(engine)
    return True

def get_connection_string():
    """Get the database connection string."""
    return DATABASE_URL

# LangSmith Configuration
def setup_langsmith():
    """Configure LangSmith tracing if API key is available."""
    if LANGSMITH_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "GenAI-Class-Final"
        return True
    return False

def mark_profile_complete(student_id: str):
    """Mark a user's profile as complete after questionnaire submission."""
    try:
        engine = get_database_engine()
        from sqlalchemy import text
        query = text("""
            UPDATE student_profiles
            SET is_profile_complete = TRUE,
                last_login = :current_time,
                profile_version = profile_version + 1
            WHERE student_id = :student_id
        """)

        with engine.connect() as conn:
            conn.execute(query, {
                "student_id": student_id.strip(),
                "current_time": datetime.now(timezone.utc)
            })
            conn.commit()
            print(f"Marked profile complete for {student_id}")

    except Exception as e:
        print(f"Error marking profile complete for {student_id}: {e}")