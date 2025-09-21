"""
Database Configuration Module
Centralizes all database connections, environment variables, and table definitions.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, String, Text, MetaData, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from datetime import datetime, timezone
import uuid

# Load environment variables
load_dotenv()

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