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
    """Get database engine with lazy initialization and proper connection pooling."""
    global _engine
    if _engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable not set.")

        # Configure connection pool for Supabase
        _engine = create_engine(
            DATABASE_URL,
            pool_size=5,          # Maximum number of persistent connections
            max_overflow=10,      # Maximum number of connections that can be created beyond pool_size
            pool_timeout=30,      # Number of seconds to wait before giving up on getting a connection
            pool_recycle=1800,    # Number of seconds after which a connection is discarded and replaced
            pool_pre_ping=True,   # Validate connections before use
            connect_args={
                "connect_timeout": 10,  # Connection timeout in seconds
                "application_name": "Clare-AI-Streamlit"
            }
        )
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
    Column('student_name', String(255), nullable=True),
    Column('is_profile_complete', Boolean, nullable=False, default=False),
    Column('last_login', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)),
    Column('profile_version', Integer, nullable=False, default=1),
    Column('timestamp', DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)

def create_tables():
    """Create all tables if they don't exist."""
    engine = get_database_engine()
    try:
        # Use a connection context manager to ensure proper cleanup
        with engine.connect() as conn:
            metadata.create_all(bind=conn)
            conn.commit()
        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise

def get_connection_string():
    """Get the database connection string."""
    return DATABASE_URL

def close_all_connections():
    """Close all database connections and dispose of the engine."""
    global _engine
    if _engine is not None:
        try:
            _engine.dispose()
            print("Database connections closed successfully")
        except Exception as e:
            print(f"Error closing database connections: {e}")
        finally:
            _engine = None

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

def store_student_name(student_id: str, student_name: str):
    """Store or update the student name for a user."""
    try:
        engine = get_database_engine()
        from sqlalchemy import text

        # First check if a profile exists for this student
        check_query = text("""
            SELECT id FROM student_profiles
            WHERE student_id = :student_id
            LIMIT 1
        """)

        with engine.connect() as conn:
            existing_profile = conn.execute(check_query, {"student_id": student_id.strip()}).fetchone()

            if existing_profile:
                # Update existing profile with student name
                update_query = text("""
                    UPDATE student_profiles
                    SET student_name = :student_name
                    WHERE student_id = :student_id
                """)
                conn.execute(update_query, {
                    "student_id": student_id.strip(),
                    "student_name": student_name.strip()
                })
            else:
                # Create new profile entry with student name
                insert_query = text("""
                    INSERT INTO student_profiles (id, student_id, student_name, profile_summary, is_profile_complete, timestamp)
                    VALUES (:id, :student_id, :student_name, :profile_summary, :is_profile_complete, :timestamp)
                """)
                conn.execute(insert_query, {
                    "id": uuid.uuid4(),
                    "student_id": student_id.strip(),
                    "student_name": student_name.strip(),
                    "profile_summary": {},
                    "is_profile_complete": False,
                    "timestamp": datetime.now(timezone.utc)
                })

            conn.commit()
            print(f"Stored student name '{student_name}' for {student_id}")

    except Exception as e:
        print(f"Error storing student name for {student_id}: {e}")