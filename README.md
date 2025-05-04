# Overall Nodes Design

![Imgur](https://imgur.com/LXaHZG2.png)

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

Student profile exmaple:

Here is the record for student "Alex Chen":

Subhect:
- Homework 1: Score 92, On-time, Comment: "Thorough understanding"
- Homework 2: Score 78, Late submission, Comment: "Partial misunderstanding on key concept"

Quizzes:
- Quiz 1: 6/10, Mistakes: "Formula confusion on Q2"
- Quiz 2: 8/10, Mistakes: "Missed definition in Q3"

Class Interactions:
- Asked 2 questions during sessions
- No forum posts

Generate a 3–4 sentence summary for this student.

Example Summary:
Alex consistently completes assignments with generally good understanding, though sometimes struggles with key concepts, as seen in Homework 2. 
They performed reasonably well in quizzes, with recurring issues in concept clarity, especially around formula application. 
They participate during live sessions by asking questions but are inactive on the course forum. 
Encourage deeper review of core definitions and continued engagement in class discussions.