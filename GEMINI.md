# Project Overview

This project, "Clare-AI," is a teaching assistant chatbot for a Generative AI course (IST 345) at Claremont Graduate University. It's built with Python and utilizes a sophisticated agentic workflow to answer student questions. The front end is a web interface created with Streamlit.

## Key Technologies

*   **Core Framework:** LangChain and LangGraph are used to build the agentic workflow.
*   **LLMs:** The application uses OpenAI's `gpt-4o` and `gpt-4o-mini` models.
*   **Embeddings:** OpenAI's `text-embedding-3-large` is used for creating vector embeddings.
*   **Vector Store:** PostgreSQL with the `pgvector` extension is used for storing and retrieving documents. The project uses a cloud-hosted Supabase instance.
*   **Web Search:** The Tavily API is used for real-time web searches.
*   **Frontend:** Streamlit is used to create the user interface.
*   **Database:** SQLAlchemy is used to interact with the PostgreSQL database.
*   **Feedback:** LangSmith is integrated for collecting and monitoring feedback on the AI's responses.

## Architecture

The application is designed around a "GraphState" that represents the state of the conversation. The workflow is a series of nodes that are conditionally executed based on the state. The main components of the architecture are:

1.  **Query Router:** This node analyzes the user's question and routes it to the appropriate data source: the vector store, a web search, or a "chitter-chatter" agent for off-topic questions.
2.  **Document Retriever:** This node retrieves relevant documents from the PGVector store using a multi-query RAG-fusion approach with MMR (Maximal Marginal Relevance) for diverse results.
3.  **Relevance Grader:** This node evaluates the relevance of the retrieved documents to the user's question.
4.  **Web Searcher:** This node performs a web search using the Tavily API if the vector store does not contain sufficient information.
5.  **Answer Generator:** This node generates a natural language answer based on the retrieved context and the student's learning profile.
6.  **Hallucination Checker:** This node verifies that the generated answer is grounded in the provided documents.
7.  **Answer Verifier:** This node checks if the generated answer is relevant to the user's question.
8.  **Query Rewriter:** This node rewrites the user's question if the initial answer is not satisfactory.
9.  **Student Profiling:** The application builds a profile of each student's learning based on their interactions. This is used to personalize the AI's responses.

# Building and Running

## 1. Installation

To run this project, you need to have Python installed. Then, you can install the required dependencies from the `requirements-Win.txt` or `requirements-Mac.txt` file:

```bash
# For Windows
pip install -r requirements-Win.txt

# For macOS
pip install -r requirements-Mac.txt
```

## 2. Environment Variables

The application requires several environment variables to be set in a `.env` file. 

*   `DATABASE_URL`: The connection string for the Supabase PostgreSQL database.
*   `OPENAI_API_KEY`: Your API key for the OpenAI API.
*   `TAVILY_API_KEY`: Your API key for the Tavily Search API.
*   `LANGSMITH_API_KEY`: Your API key for LangSmith.
*   `LLAMA_CLOUD_API_KEY`: Your API key for Llama Cloud.

## 3. Running the Application

The application is a Streamlit app. To run it, use the following command:

```bash
streamlit run main.py
```

# Development Conventions

*   **Modular Architecture:** The code is organized into modules within the `src` directory, separating concerns like authentication, database interactions, and the agentic workflow.
*   **Type Hinting:** The code uses type hints for better readability and maintainability.
*   **Stateful Workflow:** The core logic is built around a stateful graph using LangGraph, which allows for complex, conditional workflows.
*   **Async/Await:** The project uses `async/await` patterns extensively, especially in the agentic workflows.
*   **Error Handling:** The code includes `try...except` blocks to handle potential errors, such as configuration errors and API failures.
*   **Feedback Loop:** The application integrates with LangSmith to collect user feedback, which is crucial for improving the AI's performance.
*   **Prompt Engineering:** The prompts for the LLMs are clearly defined in the `src/prompts/system_prompts.py` file.

# Project History

The project has undergone a significant refactoring from a monolithic architecture to a modular one. The original, monolithic code is preserved in the `legacy` directory. This refactoring has improved the project's organization, maintainability, and scalability.