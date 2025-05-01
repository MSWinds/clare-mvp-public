# Overall Nodes Design

![Imgur](https://imgur.com/x3IEq6K.png)

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


## Agents Checklist
- (WIP)Same Question Check: I am thinking of combinining same question check and chitterchatter and I have added the nodes and prompt but i dont know how to test it or how to make it start on the node
- Satisfactory Check
- ✅Query Router
- ✅Chitter-Chatter(TA info)
- ✅Document Retriever
- ✅Relevance Grader
- ✅Web Searcher
- (WIP need to include long term memoty later but it works for now)✅ Hint Generator
- ✅ Hallucination Checker
- ✅ Answer Verifier
- ✅ Query Rewriter