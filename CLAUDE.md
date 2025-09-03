# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains **Clare-AI**, an AI teaching assistant for a Generative AI course at Claremont Graduate University. The system uses LangGraph workflows to provide intelligent, educational responses while tracking student interactions and learning profiles.

## Architecture

### Core Components

**Main Application (`main.py`)**
- Streamlit-based web interface for student interactions
- Handles chat history, feedback collection, and database storage
- Integrates with LangSmith for tracing and evaluation
- Manages student ID tracking and profile generation

**Agentic Workflow (`agentic_workflow.py`)**
- LangGraph-based workflow engine with multiple specialized agents:
  - **Query Router**: Routes questions to vectorstore, web search, or chit-chat
  - **Document Retriever**: Multi-query RAG with MMR and Reciprocal Rank Fusion
  - **Relevance Grader**: Async document relevance evaluation
  - **Answer Generator**: Personalized teaching assistant responses
  - **Hallucination Checker**: Validates responses against source documents  
  - **Answer Verifier**: Ensures responses address the original question
  - **Query Rewriter**: Rewrites queries for better retrieval
  - **Chitter-Chatter**: Handles off-topic conversations

**Student Profiling (`summarizer.py`)**
- Async LangGraph workflow for generating student learning profiles
- Analyzes chat history to provide personalized teaching recommendations
- Stores profiles in PostgreSQL for retrieval during conversations

**Document Processing (`doc_processing.py`)**
- PDF processing with PyMuPDF4LLM and LlamaParse
- Metadata extraction and tagging using OpenAI functions
- Token-aware chunking and batch uploading to PGVector
- Markdown header-based document splitting

## Database Schema

**PostgreSQL with pgvector extension**
- `chat_history`: Stores user inputs and AI responses with timestamps
- `student_profiles`: Contains generated learning profiles for personalization
- `final_data`: Vector embeddings collection for course materials

## Development Commands

### Environment Setup
```bash
# Install Python dependencies
pip install -r requirements-Win.txt  # Windows
pip install -r requirements-Mac.txt  # macOS

# Set up environment variables in .env file:
# OPENAI_API_KEY=your_openai_api_key
# DB_CONNECTION=postgresql://user:pass@host:port/db
# TAVILY_API_KEY=your_tavily_api_key  
# LANGSMITH_API_KEY=your_langsmith_api_key
# LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
```

### Running the Application
```bash
# Start the Streamlit interface
streamlit run main.py

# Process and upload documents to vector database
python doc_processing.py

# Test student profile generation
python summarizer.py
```

### Development Workflow
- The system uses **async/await** patterns extensively - ensure compatibility when modifying workflows
- **LangSmith integration** provides tracing - configure project name in `agentic_workflow.py:58`
- **Multi-query RAG** with RRF reranking improves retrieval quality
- **Token counting** prevents batch upload failures - maintain token limits in processing scripts

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

## Important Notes

- **Database connections** use SQLAlchemy with connection pooling
- **Embedding model**: `text-embedding-3-large` for high-quality vectors
- **LLM models**: GPT-4o for complex tasks, GPT-4o-mini for simple operations
- **Async processing** throughout - use `ainvoke()` and `await` patterns
- **Error handling** includes graceful fallbacks and user-friendly messages