#  Environment Configuration
from dotenv import load_dotenv  
import os
from sqlalchemy.engine.url import make_url # Used to parse and construct database URLs
from langchain_postgres.vectorstores import PGVector # Integration with Postgres + pgvector for vector storage

# LLM and Core LangChain Tools
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI

from langchain_core.messages import HumanMessage, SystemMessage
from langchain.load import dumps, loads  # Serialize/deserialize LangChain objects
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser 
from langchain_core.documents import Document # # Standard document format used in LangChain pipelines

from typing_extensions import TypedDict # Define structured types for state management
from typing import List  # Specify types for list inputs or outputs
import asyncio # Support asynchronous execution for parallel LLM calls

from langgraph.graph import StateGraph, END # LangGraph tools to define stateful workflows 

# # Import the `trace` decorator from LangSmith to enable tracing of some individual customized function calls and metadata for observability/debugging.
# from langsmith import trace

from sqlalchemy import create_engine, text, Table, Column, MetaData, UUID, Text, DateTime
from datetime import datetime, timezone
import uuid

# --- table structure ---
# current_student_id = "123456"
metadata = MetaData()
chat_table = Table(
    'chat_history', metadata,
    Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4), # Added default for clarity
    Column('student_id', Text, nullable=False),
    Column('user_input', Text, nullable=False),
    Column('ai_response', Text, nullable=False),
    Column('timestamp', DateTime(timezone=True), default=datetime.now(timezone.utc))
)


# Load environment variables from .env file
load_dotenv()

# Access the environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
connection_string = os.getenv("DB_CONNECTION")
tavily_api_key = os.getenv("TAVILY_API_KEY")

langsmith_api_key = os.getenv("LANGSMITH_API_KEY")

# Enable LangSmith tracing for observability/debugging
os.environ["LANGCHAIN_TRACING"] = "true"
# Set the project name for LangSmith, it will create a new project if it doesn't exist
os.environ["LANGCHAIN_PROJECT"] = "GenAI-Class-Final"

# Configure Database Connection
# Use the same shared table as from the last lab
# shared_connection_string = make_url(connection_string)\
#     .set(database="GenAI_Spring25_Shengjie_Qian_db").render_as_string(hide_password=False) # Leave password visible for local testing

# Initialize the embedding model
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
print("-------- new Conversation ---------")
# Quick check environment variables
if not openai_api_key or not connection_string or not tavily_api_key or not embedding_model or not langsmith_api_key:
    print(f"Error: Missing one or more required environment variables") # If so, print out your key to check
else:
    print("All environment variables loaded successfully")


# Main LLM for handling complex or creative tasks
llm_gpt = ChatOpenAI(
    model="gpt-4o", # GPT-4o is a powerful model with strong reasoning capabilities
    temperature=0.5,
    api_key=openai_api_key
)

# Lightweight LLM for simple or deterministic tasks
llm_gpt_mini = ChatOpenAI(
    model="gpt-4o-mini",    #  Smaller, faster variant for lightweight tasks
    temperature=0,          # Temperature 0 = fully deterministic output
    api_key=openai_api_key
)

# Connect to the PGVector Vector Store that contains book data.
book_data_vector_store = PGVector(
    embeddings=embedding_model,   
    collection_name="final_data",   # Name of the collection/table in the vector DB
    connection=connection_string, # Use shared DB connection from earlier
    use_jsonb=True, 
)

