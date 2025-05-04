# Design an evaluation pipeline

Design an evaluation pipeline for the chatbot that ensures functional correctness, instruction-following, factual consistency, and safety. The plan should consider both user experience and technical quality.

## Step 1: Decompose and Evaluate System Components

| Component                  | Successful Performance                                  | Potential Failure Points                                | Evaluation Targets                                                                 |
| :------------------------- | :----------------------------------------------------- | :------------------------------------------------------ | :--------------------------------------------------------------------------------- |
| Intent Classification      | Correctly identifies user's intent                     | Misinterpretation, ambiguity, out-of-scope queries      | Accuracy, precision, recall; F1-score; handling of out-of-scope queries.          |
| Retrieval System           | Retrieves relevant documents/data from knowledge base  | Incorrect or incomplete retrieval, lack of context      | Recall of relevant information, precision of retrieved data, relevance score, context coverage. |
| Intermediate Agent Reasoning | Correctly reasons through multi-step tasks             | Logical errors, failure to integrate information        | Accuracy of reasoning steps, logical consistency, ability to synthesize information, correctness of intermediate outputs. |
| Response Generation        | Generates coherent, relevant, and accurate responses    | Inaccuracy, irrelevance, poor formatting, inappropriate tone | Factuality, relevance, coherence, fluency, tone, formatting correctness, instruction following. |
| Output Formatting          | Presents information in a clear, structured way         | Incorrect formatting, missing information, poor readability | Format correctness, readability, clarity, inclusion of all requested information. |
| Safety/Moderation          | Filters out harmful or inappropriate content            | Failure to detect sensitive topics, generating toxic output | Detection rate of harmful content, false positive rate, adherence to safety guidelines.        |

---

## Step 2: Define Evaluation Categories and Perspectives

| Capability Category     | Type          | Metric                             | Description                                                               | Rationale                                                                                      |
| :---------------------- | :------------ | :--------------------------------- | :------------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------- |
| Domain-Specific         | Technical     | Accuracy                           | Percentage of relevant and accurate information retrieved.                | Ensures the chatbot provides reliable CGU data.                                                |
| Domain-Specific         | User-centric  | Relevance                          | User rating of how relevant the information was to their query.           | Measures how effectively the chatbot addresses user needs within the CGU domain.               |
| Generation              | Technical     | Factuality                         | Percentage of generated responses that are factually correct.             | Ensures the chatbot provides accurate and truthful information.                                |
| Generation              | User-centric  | Coherence and Fluency              | User rating of the clarity and naturalness of the chatbot's responses.    | Measures the quality of the generated text from a user perspective.                            |
| Instruction-Following   | Technical     | Compliance                         | Percentage of responses that adhere to specific requirements.             | Ensures the chatbot can follow instructions and present information clearly.                   |
| Instruction-Following   | User-centric  | Completeness of Response           | User rating of how completely the chatbot addressed their query.          | Measures if the chatbot fully answered the user's question and provided all necessary information. |
| Efficiency              | Technical     | Response Latency                   | Time taken to generate a response.                                        | Measures the efficiency of the chatbot, ensuring quick and responsive interactions.            |
| Efficiency              | Technical     | Resource Used                      | Amount of computational resources used per conversation.                  | Optimizes the model for efficient use of resources.                                             |
| Safety/Moderation       | Technical     | Detection Rate of Harmful Content  | Percentage of harmful or inappropriate content detected.                  | Ensures the chatbot does not generate or propagate harmful or inappropriate content.           |
| Safety/Moderation       | User-centric  | User Trust and Safety Perception   | User rating of how safe and trustworthy the chatbot's responses were.     | Measures the user's confidence in the chatbot's reliability.                                   |


## Step 3: Create Evaluation Guidelines

Detailed Scoring System (Rubric/Checklist)

1.  **Domain-Specific: Accuracy of Information Retrieval (Technical)**
    -   **Metric:** Percentage of relevant and accurate information retrieved.
    -   **Observable Indicators:**
        -   Correct facts from the knowledge base.
        -   No irrelevant or outdated information.
        -   Answer all aspects of the user's query.
    -   **Methods:**
        -   **Automated (With additional LLMs):**
            -   Compare retrieved text against known facts in the knowledge base using semantic similarity (cosine similarity of embeddings).
            -   Use a database query validation script to verify that the retrieved data matches the expected values.
        -   **Manual:**
            -   Rubric Scoring (1-5 scale):
                -   1: No relevant information retrieved.
                -   2: Little relevant information.
                -   3: Some relevant information, but with inaccuracies or omissions.
                -   4: Most relevant information retrieved with little omissions.
                -   5: All relevant information retrieved accurately.

2.  **Domain-Specific: Relevance of Information Provided (User-centric)**
    -   **Metric:** User rating of how relevant the information was to their query.
    -   **Observable Indicators:**
        -   User feedback ratings (thumbs up or down).
        -   User comments indicating relevance or irrelevance in the streamlit comment section.
    -   **Methods:**
        -   **Automated:**
            -   Analyze user feedback ratings.
            -   Analyze user feedback comments using sentiment analysis to determine if the comment indicates the response was relevant or irrelevant.
        -   **Manual:**
            -   Analyze user feedback comments built within streamlit for specific mentions of relevance.

3.  **Generation: Factuality (Technical)**
    -   **Metric:** Percentage of generated responses that are factually correct.
    -   **Observable Indicators:**
        -   Consistency with verified information in the knowledge base.
        -   Absence of contradictions or false statements.
    -   **Methods:**
        -   **Automated:**
            -   Check if the generated response is entailed by the retrieved information.
            -   Compare generated text against known facts in the database.
        -   **Manual:**
            -   Rubric Scoring (1-5 scale):
                -   1: Response contains significant factual errors.
                -   2: Response contains mostly factual errors, but contains little facts.
                -   3: Response contains some factual errors or omissions.
                -   4: Response contains almost no factual errors or omissions.
                -   5: Response is completely factually accurate.

4.  **Generation: Coherence and Fluency (User-centric)**
    -   **Metric:** User rating of the clarity and naturalness of the chatbot's responses.
    -   **Observable Indicators:**
        -   Grammatical correctness.
        -   Logical flow and organization of information.
        -   Conversational language usage
    -   **Methods:**
        -   **Automated:**
            -   Measure the model's uncertainty in predicting the next word.
            -   Compare generated text to reference responses.
        -   **Manual:**
            -   Rubric Scoring (1-5 scale):
                -   1: Response is incoherent and difficult to understand.
                -   2: Response has some readability but is mostly hard to understand.
                -   3: Response is somewhat coherent but contains grammatical errors or awkward phrasing.
                -   4: Response has minor language errors.
                -   5: Response is clear, fluent, and grammatically correct.

5.  **Instruction-Following: Compliance with Format Instructions (Technical)**
    -   **Metric:** Percentage of responses that adhere to specific formatting requirements.
    -   **Observable Indicators:**
        -   Correct formatting of lists, tables, and other structured data.
        -   Inclusion of all requested information in the specified format.
    -   **Methods:**
        -   **Automated:**
            -   Regular expression checks for format compliance.
            -   Parsing for structured data (JSON, XML) to verify correctness.
        -   **Manual:**
            -   Checklist:
                -   [ ] All requested data is present.
                -   [ ] Data is formatted correctly.
                -   [ ] The response follows all format specifications.

6.  **Instruction-Following: Completeness of Response (User-centric)**
    -   **Metric:** User rating of how completely the chatbot addressed their query.
    -   **Observable Indicators:**
        -   All parts of the query are addressed.
        -   No relevant information is missing.
    -   **Methods:**
        -   **Automated:**
            -   Analyze the generated text to ensure all the keywords present in the query have been addressed.
        -   **Manual:**
            -   Rubric Scoring (1-5 scale):
                -   1: Response fails to address the query.
                -   2: Response is about the query but does not address the query.
                -   3: Response partially addresses the query, but misses key information.
                -   4: Response has minor hiccups but the answer is mostly satisfactory.
                -   5: Response fully and completely addresses the query.

7.  **Cost and Latency: Response Latency (Technical)**
    -   **Metric:** Time taken to generate a response.
    -   **Observable Indicators:**
        -   Time taken for each step in the LLM application's execution in Langsmith (retrieval, LLM call …etc).
        -   Overall response time.
    -   **Methods:**
        -   **Automated (LangSmith):**
            -   LangSmith tracing captures the latency of each operation.
            -   LangSmith dashboards display latency metrics over time.
            -   LangSmith monitoring can alert when latency exceeds thresholds.
        -   **Manual:**
            -   Record the time taken for the chatbot to respond to a set of queries.
            -   Compare response times across different versions of the application.
            -   Rubric Scoring (1-3 scale):
                -   1: Very slow response time, unacceptable for user experience. (>1minute)
                -   2: Acceptable response time, but room for improvement. (~30s)
                -   3: Very fast, and efficient response time. (~10s)

8.  **Cost and Latency: Resource Utilization (Technical)**
    -   **Metric:** Amount of computational resources used per conversation.
    -   **Observable Indicators:**
        -   Token usage (input and output).
        -   API call costs.
        -   Computational time.
    -   **Methods:**
        -   **Automated (LangSmith):**
            -   LangSmith tracing captures token usage for LLM calls.
            -   Langsmith can be used to track API call costs, when those are integrated.
            -   Langsmith can track computational time.
            -   Langsmith dashboards can display token usage and estimated cost.
        -   **Manual:**
            -   Calculate the average token usage per conversation.
            -   Monitor API call costs.
            -   Record the amount of computational resources used during the conversations.
            -   Rubric Scoring (1-3 scale):
                -   1: Very high resource usage, leading to high cost.
                -   2: Moderate resource usage, acceptable but could be optimized.
                -   3: Very efficient resource usage, minimal cost.

9.  **Safety/Moderation: Detection Rate of Harmful Content (Technical)**
    -   **Metric:** Percentage of harmful or inappropriate content detected.
    -   **Observable Indicators:**
        -   Flags raised by toxicity detection models.
        -   Manual review of responses for sensitive topics, bias, and inappropriate content.
    -   **Methods:**
        -   **Automated:**
            -   Use pre-trained toxicity detection models.
            -   Use regular expressions to detect unwanted words.
        -   **Manual:**
            -   Checklist:
                -   [ ] No toxic language present.
                -   [ ] No biased language present.
                -   [ ] No sensitive information revealed.

10. **Safety/Moderation: User Trust and Safety Perception (User-centric)**
    -   **Metric:** User rating of how safe and trustworthy the chatbot's responses were.
    -   **Observable Indicators:**
        -   User feedback ratings.(thumb up and down)
        -   User comments expressing trust or distrust.
    -   **Methods:**
        -   **Automated:**
            -   Analyze sentiment of user comments.(positive or negative)
        -   **Manual:**
            -   Review user comments for expressions of trust or distrust.

## Step 4: Define Evaluation Methods and Data

The evaluation techniques and tools and a diverse test set for a Claremont Graduate University (CGU) chatbot.

### Evaluation Techniques and Tools

1.  **LLM-as-a-Judge (GPT-4o-mini):**
    -   We'll use GPT-4o-mini to evaluate the chatbot's responses against our defined criteria (by importing the 10 criteria above).
    -   **Prompts:** We'll craft detailed prompts that specify the evaluation criteria and ask GPT to provide a score and rationale for each response according to our guidelines above.
2.  **Natural Language Inference (NLI) (huggingface:sentence-transformers/nli-roberta-base-v2):**
    -   We'll use NLI models to assess the factual consistency of the chatbot's responses against the retrieved information.
    -   **Scripts:** Python scripts will be created that utilize the hugging face transformers library to run the NLI models.
3.  **Regular Expression Checks (Python):**
    -   For instruction-following (format compliance), we'll use regular expressions to validate the structure of the chatbot's output (e.g., dates, lists, contact information).
    -   **Scripts:** Python scripts will be created that implement the regular expressions.
4.  **Human Evaluation:**
    -   Human evaluators will assess the chatbot's responses using the rubrics and checklists we defined earlier.
5.  **LangSmith:**
    -   Langsmith will be used to track latency, token usage, and for general monitoring of the chatbot.
    -   Langsmith also contains thumbs up and down metric in addition to user comments for manual evaluation.

### Test Set for CGU Chatbot

Here's a representative test set of 10 queries, designed to trigger different paths in a CGU chatbot's multi-agent workflow:

1.  **Query:** "What are the application deadlines for the PhD in Information Systems & Technology?"
    -   **Intended Path:** Retrieval of program-specific deadlines + up to date websearch.
    -   **Reference Response:** "The application deadline for the PhD in Information Systems & Technology is [Date]. Please check the official program website for any updates."
2.  **Query:** "Tell me about available scholarships for international students in the psychology program."
    -   **Intended Path:** Retrieval of financial aid information from web search after failure to find relevant info from database.
    -   **Reference Response:** "CGU offers several scholarships for international students in the psychology program, including [Scholarship Names]. You can find more details on the financial aid website."
3.  **Query:** "Where is the Career Services office located, and what are their hours?"
    -   **Intended Path:** Retrieval of web search ONLY skipping database.
    -   **Reference Response:** "The Career Services office is located in [Building] and is open from [Hours]. You can also schedule appointments online."
4.  **Query:** "What events are happening on campus next week?"
    -   **Intended Path:** Retrieval of web search ONLY skipping database.
    -   **Reference Response:** "Next week, CGU will host [Event 1], [Event 2], and [Event 3]. You can find a full list of events on the university calendar."
5.  **Query:** "How do I request an official transcript?"
    -   **Intended Path:** Retrieval from web search, may include database.
    -   **Reference Response:** "You can request an official transcript through the student portal or by contacting the Registrar's Office at [Contact Information]."
6.  **Query:** "What courses are offered in the Master's in Public Health program?"
    -   **Intended Path:** Retrieval from database ONLY.
    -   **Reference Response:** "The Master's in Public Health program offers courses such as [Course 1], [Course 2], and [Course 3]. Please refer to the program catalog for a complete list."
7.  **Query:** "What are the core requirements for the Masters DBOS program?"
    -   **Intended Path:** Retrieval from database ONLY.
    -   **Reference Response:** "The Masters DBOS program requires [Requirement 1], [Requirement 2], and [Requirement 3]. More details can be found on the program website."
8.  **Query:** "Give me a checklist of items to complete to get a Phd for CISAT."
    -   **Intended Path:** web search + database
    -   **Reference Response:** "The Honnold/Mudd Library is located at [Address]. It provides access to [Resources], including online databases and research support." *(Note: This reference response seems mismatched to the query)*
9.  **Query:** "What are the criticisms of the current US administration’s policies?"
    -   **Intended Path:** NOT CGU.
    -   **Reference Response:** "Unable to answer the questions regarding CGU. Please let me know if you have any questions regarding CGU."
10. **Query:** "What classes should you take to get into UCSD’s CISAT major?"
    -   **Intended Path:** NOT CGU.
    -   **Reference Response:** "Unable to answer the questions regarding CGU. Please let me know if you have any questions regarding CGU."

## Step 5: Implement Multi-Level Evaluation and Feedback Loops

### Continuous Turn-Based Evaluation & Automated Logging

-   **Process:** After each response, automatically run evaluations (LLM-as-judge, NLI, etc.) and log all data (query, response, metrics, latency, token usage). Flag responses below performance thresholds. Implement a reward system for high scores to refine responses.
-   **Goal:** Quickly identify and fix specific errors (factuality, relevance, latency) in individual responses.

### Task-Based User Feedback & Conversation Analysis

-   **Process:** After each conversation, prompt users for feedback (ratings, comments). Analyze conversation length, task completion, and user satisfaction.
-   **Goal:** Improve overall conversation flow, context handling, and user satisfaction by addressing systemic issues.

### Data-Driven System Design Improvements

-   **Process:** Regularly analyze evaluation data and user feedback to identify trends and patterns (Langsmith).
-   **Goal:** Implement enhancements (dynamic retrieval, memory optimization, intent classification retraining) to address recurring problems and improve long-term performance.