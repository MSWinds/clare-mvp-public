# Overall Nodes Design

![Logo](https://imgur.com/a/WL55IGY)


## Initial Pipline

- **Query Router**  
  Routes user queries to appropriate nodes.

- **Query Rewriter**  
  cahnge queries for improved retrieval performance.

- **Similarity Checker**  
  Compares current question and previous to check for continuity.

- **Web Searcher**  
  web search agent to gather real-time information.

- **Doc Retriever**  
  Retrieves relevant documents or passages from database.

- **Relevance Grader**  
  Scores documents/passages for relevance to the original or rewritten query.

## Answer Pipeline

- **Answer Generator**  
  Generates a natural language answer withs tep by step guiding thinking based on retrieved content.

- **Hallucination Checker**  
  Detects unsupported or made-up content in generated answers.

- **Answer Checker**  
  Evaluates factual accuracy and completeness related to retreived doc of generated answers.

## Output

- **Answer**  
  Final, user-facing response.

## Interface

- **Streamlit (Frontend)**  
  web-based interface for user interaction and used to fetch previous question.
