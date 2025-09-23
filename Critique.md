# LangGraph & Prompt Design Critique

## 1. Executive Summary (TL;DR)

This document analyzes the design of the Clare-AI agentic workflow. While the system demonstrates a sophisticated architecture for handling complex, research-oriented questions, it currently struggles with simple, factual queries.

-   **Core Problem:** The system is over-engineered for simple FAQ-style questions ("Who is our TA?"). It incorrectly treats them as complex research queries, leading to inefficient, costly, and incorrect responses through unnecessary loops of retrieval, web search, and query rewriting.
-   **Root Cause:** This issue stems from two primary areas:
    1.  **Ambiguous Routing Prompt:** The initial `query_router` prompt classifies questions based on *content domain* (course-related vs. off-topic) rather than *user intent* (simple fact-finding vs. deep explanation).
    2.  **Rigid Graph Structure:** The LangGraph architecture has a "one-way street" design. Once a query is routed down the complex retrieval path, there are no "off-ramps" or mechanisms to de-escalate it to a simpler path, even when retrieval consistently fails.
-   **Key Recommendations:**
    1.  **Refine the Router:** Re-engineer the `query_router_prompt` to classify query intent and add a new category for "Simple/FAQ" questions.
    2.  **Add Architectural Flexibility:** Modify the LangGraph to include fallback mechanisms. For instance, after a complete retrieval failure, a new node should re-evaluate the question's nature before defaulting to a web search.

---

## 2. LangGraph Design Analysis

The graph's structure is powerful but reveals a bias towards a single type of user interaction.

### Strengths

-   **Sophisticated Retrieval for Complex Queries:** The use of RAG-Fusion (`multi_query_generation_prompt`) and MMR in the `DocumentRetriever` is an excellent, advanced technique for improving the quality of retrieved context for nuanced questions.
-   **Robust Self-Correction Loop:** The `AnswerVerifier` -> `QueryRewriter` cycle is a powerful mechanism for iteratively refining queries to find answers to difficult questions. This shows a mature understanding of agentic design patterns.
-   **Clean State Management:** The `GraphState` TypedDict provides a clear and organized way to manage and pass information between nodes, which is crucial for complex graphs.
-   **Personalization:** The integration of the `profile_analyzer` to inject learner context into the `AnswerGenerator` is a standout feature that enables personalized, pedagogically effective responses.

### Areas for Improvement

1.  **The "Single Point of Failure" Router:** The entire workflow's efficiency and correctness hinge on the first decision made by `route_question`. An incorrect initial routing (as seen in the "TA" example) sends the entire system down a costly and inappropriate path from which it cannot recover.
2.  **Rigid Failure Pathways:** The graph currently operates on a key assumption: "If our internal documents don't have the answer, the user must want a web search." The `RelevanceGrader` node, upon filtering all documents, unconditionally triggers the `WebSearcher`. This ignores other possibilities, such as the question being a simple FAQ that was never meant for deep retrieval in the first place.
3.  **The Misapplied Rewrite Loop:** The self-correction loop is a "feature" for complex questions but becomes a "bug" for simple ones. When asked "whos our ta?", the system fails, web searches, and then the `AnswerVerifier` correctly identifies the generic web answer is useless. However, the `QueryRewriter` then "optimizes" the simple question into a more complex one (`"...as listed in the course syllabus?"`), pushing the system further down the wrong path instead of recognizing the initial premise was flawed.

---

## 3. Prompt Engineering Analysis

The prompts are well-structured but, like the graph, are optimized for one primary task.

### Strengths

-   **Clear and Structured:** The use of Markdown headers (### Role & Goal ###, ### Instructions ###, etc.) provides excellent structure. This makes prompts easy to read, maintain, and understand for both humans and the LLM.
-   **Separation of Concerns:** Each prompt corresponds to a distinct, single-responsibility agent (`RelevanceGrader`, `HallucinationChecker`, etc.). This modularity is a best practice that improves reliability.

### Areas for Improvement

1.  **`query_router_prompt` - The Primary Culprit:**
    -   **Problem:** The prompt forces a choice between `Vectorstore`, `Websearch`, and `Chitter-Chatter` based on whether the topic is "course-related." A question like "who is the TA?" is factually course-related, so the LLM correctly chooses `Vectorstore`, ignoring the simplicity of the query. The prompt fails to distinguish between a "research question" and a "lookup question."
    -   **Recommendation:** Modify the prompt to classify based on **intent**. Introduce a new category like `Simple-FAQ`. Train the router to recognize question patterns.
        -   `Simple-FAQ`: "Who," "what," "where," "when" questions seeking a single, discrete piece of information. (e.g., "Who is the TA?", "When is the deadline for Lab 2?").
        -   `Vectorstore`: "How," "why," "explain," "compare" questions that require synthesis and explanation based on course concepts.
        -   `Chitter-Chatter`: Genuinely off-topic or conversational queries.

2.  **`chitterchatter_prompt` - An Underutilized Agent:**
    -   **Problem:** This agent is currently just a fallback for off-topic questions. It could be much more useful.
    -   **Recommendation:** Elevate `ChitterChatter` to be the `Simple-FAQ` handler. Its prompt could be given a small amount of static context (like the professor and TAs' contact info) so it can answer these questions directly and instantly without any external tools. For other simple questions it can't answer, it can provide a helpful, canned response pointing the user to the right resources.

3.  **`query_rewriter_prompt` - Needs More Context:**
    -   **Problem:** The prompt always assumes the goal is to make the query *more complex and specific* for vector search.
    -   **Recommendation:** This isn't a prompt issue as much as a graph state issue. The graph could pass a flag to this node indicating *why* the rewrite is happening. For example, if the state included `rewrite_reason: "answer_did_not_address_question"`, the agent could try to make the query better. If the state could indicate `rewrite_reason: "initial_retrieval_failed_completely"`, the agent could potentially simplify the query or suggest a different approach.

---

## 4. Actionable Recommendations

### Immediate Fixes (Low Effort, High Impact)

1.  **Modify `query_router_prompt`:** Immediately update the prompt to include instructions for identifying "Simple/FAQ" questions and routing them to `Chitter-Chatter`. Differentiate based on interrogative words (who/what vs. how/why).
2.  **Update `chitterchatter_prompt`:** Add the Professor and TA contact information directly into this prompt's system instructions so it can answer that specific question correctly without any external tools.

### Architectural Changes (Higher Effort)

1.  **Implement the `Simple-FAQ` Path:** Add a new conditional entry point based on the improved router's output. A route to `Chitter-Chatter` should go directly to that node and then to `END`, creating a fast, cheap "express lane" for simple questions.
2.  **Create a "Retrieval Failure" Fallback Node:** After `RelevanceGrader`, if 100% of documents are filtered out, don't go directly to `WebSearch`. Instead, go to a new conditional node called `assess_retrieval_failure`. This node would look at the *original question*. If it matches the "Simple-FAQ" pattern, it should re-route to `Chitter-Chatter`. Only if the question is complex should it proceed to `WebSearch` and the rewrite loop. This acts as a critical "safety net" to correct initial routing errors.
