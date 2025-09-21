# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **Clare-AI**, an AI teaching assistant for a Generative AI course at Claremont Graduate University. The system uses LangGraph workflows to provide intelligent, educational responses while tracking student interactions and learning profiles.

## Architecture

### Modular Structure (Post-Refactoring)

The codebase follows a clean modular architecture with organized separation of concerns:

```
src/
├── auth/                    # Authentication & user management
│   ├── authentication.py   # Session state, sign-in logic
│   └── profile_form.py     # Student questionnaire forms
├── database/               # Database configuration
│   └── config.py          # Centralized DB connection & validation
├── prompts/               # All prompt templates
│   └── system_prompts.py  # LangChain prompt templates
├── workflows/             # LangGraph agent workflows
│   ├── agentic_workflow.py # Main RAG workflow engine
│   ├── profile_analyzer.py # Student profile analysis
│   └── summarizer.py      # Profile generation workflow
└── utils/                 # Shared utilities
```

### Core Components

**Main Application (`main.py`)**
- Streamlit-based web interface (simplified from 600+ to 217 lines)
- Modular imports for clean separation of concerns
- Handles chat history, feedback collection via LangSmith
- Manages student authentication and profile management

**Agentic Workflow (`src/workflows/agentic_workflow.py`)**
- LangGraph-based workflow engine with specialized agents:
  - **Query Router**: Routes questions to vectorstore, web search, or chit-chat
  - **Document Retriever**: Multi-query RAG with MMR and Reciprocal Rank Fusion
  - **Relevance Grader**: Async document relevance evaluation
  - **Answer Generator**: Personalized teaching assistant responses using student profiles
  - **Hallucination Checker**: Validates responses against source documents
  - **Answer Verifier**: Ensures responses address the original question
  - **Query Rewriter**: Rewrites queries for better retrieval on failures
  - **Chitter-Chatter**: Handles off-topic conversations gracefully

**Authentication System (`src/auth/`)**
- `authentication.py`: Session state management, database profile retrieval
- `profile_form.py`: Complete student questionnaire with evidence conversion for profile analysis

**Database Layer (`src/database/config.py`)**
- Centralized database connection management with lazy initialization
- Environment variable validation (`DATABASE_URL`, `OPENAI_API_KEY`, etc.)
- Connection pooling via SQLAlchemy
- Supports both local PostgreSQL and cloud databases (Supabase)

**Student Profiling (`src/workflows/profile_analyzer.py`, `summarizer.py`)**
- Async LangGraph workflows for generating learning profiles
- Analyzes chat history and questionnaire responses
- Provides personalized teaching recommendations
- Stores structured profiles in PostgreSQL for retrieval

## Database Schema

**PostgreSQL with pgvector extension (Cloud-hosted on Supabase)**
- `chat_history`: User inputs and AI responses with timestamps and student IDs
- `student_profiles`: Generated learning profiles for personalization
- `langchain_pg_collection` & `langchain_pg_embedding`: Vector embeddings for course materials

## Development Commands

### Environment Setup
```bash
# Install Python dependencies
pip install -r requirements-Win.txt  # Windows
pip install -r requirements-Mac.txt  # macOS

# Set up environment variables in .env file:
# DATABASE_URL=postgresql://user:pass@host:port/db  # Supabase connection string
# OPENAI_API_KEY=your_openai_api_key
# TAVILY_API_KEY=your_tavily_api_key
# LANGSMITH_API_KEY=your_langsmith_api_key
# LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
```

### Running the Application
```bash
# Start the Streamlit interface
streamlit run main.py

# Process and upload documents to vector database (legacy)
python legacy/doc_processing.py

# Test student profile generation
python -c "import asyncio; from src.workflows.summarizer import run_profile_analysis; asyncio.run(run_profile_analysis('test_student', 'test', []))"
```

### Development Workflow
- The system uses **async/await** patterns extensively - ensure compatibility when modifying workflows
- **Environment variables** are validated at startup via `src/database/config.py:validate_env_vars()`
- **LangSmith integration** provides tracing - configure project name in `src/workflows/agentic_workflow.py`
- **Multi-query RAG** with RRF reranking improves retrieval quality
- **Modular imports** - use relative imports within src/ modules, absolute for external dependencies
- **Database migration** tools available in `legacy/migrate_to_supabase.py` for cloud deployment

## Key Features

**Educational Philosophy**
- Uses Socratic questioning instead of direct answers
- Guides students through reasoning processes
- Personalizes responses based on chat history analysis

**Retrieval System**
- Multi-query generation for diverse document retrieval
- MMR (Maximal Marginal Relevance) for result diversity
- Reciprocal Rank Fusion for improved ranking
- Fallback to web search when vectorstore lacks relevant content

**Quality Control**
- Hallucination detection against source documents
- Answer relevance verification
- Adaptive query rewriting for failed retrievals
- Retry limits to prevent infinite loops

## Data Flow

1. **User Input** → Query Router → Appropriate agent (Vectorstore/Web/Chit-chat)
2. **Document Retrieval** → Relevance Grading → Answer Generation  
3. **Quality Checks** → Hallucination & Usefulness verification
4. **Profile Updates** → Background student profile generation
5. **Feedback Loop** → LangSmith tracking for continuous improvement

## Migration & Deployment

**Database Migration**
- Migrated from VPN-dependent university database to cloud-hosted Supabase
- Migration scripts in `legacy/migrate_to_supabase.py` handle schema and data transfer
- Vector embeddings preserved using `langchain_pg_collection` and `langchain_pg_embedding` tables

**Legacy Files**
- Original monolithic code moved to `legacy/` folder
- `legacy/main_old.py` contains the original 600+ line implementation
- `legacy/doc_processing.py` handles PDF processing and vector database uploads

**Cloud Deployment**
- Ready for Streamlit Cloud deployment
- Uses environment variables for configuration
- Supabase provides managed PostgreSQL with pgvector extension

## Important Technical Notes

- **Database connections** use SQLAlchemy with connection pooling via `src/database/config.py`
- **Embedding model**: `text-embedding-3-large` for high-quality vectors
- **LLM models**: GPT-4o for complex tasks, GPT-4o-mini for simple operations
- **Async processing** throughout - use `ainvoke()` and `await` patterns
- **Error handling** includes graceful fallbacks and user-friendly messages
- **Streamlit version**: Requires recent version (1.49.1+) for proper button functionality
- **Session state management**: Handled via `src/auth/authentication.py:initialize_session_state()`