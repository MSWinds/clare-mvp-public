try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import json
from sqlalchemy.engine.url import make_url
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.load import dumps, loads
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from typing_extensions import TypedDict
from typing import List
import asyncio
from langgraph.graph import StateGraph, END
from langchain_tavily import TavilySearch
from sqlalchemy import create_engine, text, Table, Column, MetaData, UUID, Text, DateTime
from datetime import datetime, timezone
import uuid

from src.database.config import (
    OPENAI_API_KEY as openai_api_key,
    TAVILY_API_KEY as tavily_api_key,
    LANGSMITH_API_KEY as langsmith_api_key,
    get_connection_string,
    setup_langsmith
)
from src.prompts.agentic_workflow_prompts import (
    vectorstore_content_summary,
    relevant_scope,
    query_router_prompt_template,
    multi_query_generation_prompt,
    relevance_grader_prompt_template,
    answer_generator_prompt_template,
    hallucination_checker_prompt_template,
    answer_verifier_prompt_template,
    query_rewriter_prompt_template,
    chitterchatter_prompt_template
)

connection_string = get_connection_string()
setup_langsmith()

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
print("-------- new Conversation ---------")
if not all([openai_api_key, connection_string, tavily_api_key, embedding_model, langsmith_api_key]):
    print("Error: Missing one or more required environment variables")
else:
    print("All environment variables loaded successfully")

def _to_text(content):
    try:
        if isinstance(content, list):
            return "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        if isinstance(content, dict):
            return content.get("text", str(content))
        return content if isinstance(content, str) else str(content)
    except Exception:
        return str(content)

# 1. Fast & Economical: For simple, structured tasks.
llm_fast = ChatOpenAI(
    model="gpt-5-mini",
    temperature=0,
    api_key=openai_api_key,
    reasoning={"effort": "minimal"}
)

# 2. Balanced: For intermediate reasoning tasks.
llm_balanced = ChatOpenAI(
    model="gpt-5",
    temperature=0.5,
    api_key=openai_api_key,
    reasoning={"effort": "minimal"}
)

# 3. Powerful: For the final, high-quality answer generation.
llm_powerful = ChatOpenAI(
    model="gpt-5",
    temperature=0.5,
    api_key=openai_api_key,
    reasoning={"effort": "low"}
)

book_data_vector_store = PGVector(
    embeddings=embedding_model,
    collection_name="final_data",
    connection=connection_string,
    use_jsonb=True,
)

def reciprocal_rank_fusion(results, k=60):
    fused_scores = {}
    for docs in results:
        for i, doc in enumerate(docs):
            doc_str = dumps(doc)
            if doc_str not in fused_scores:
                fused_scores[doc_str] = 0
            rank = i + 1
            fused_scores[doc_str] += 1 / (rank + k)
    reranked_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    reranked_documents = []
    for doc_str, score in reranked_results:
        doc = loads(doc_str)
        doc.metadata["rrf_score"] = score
        reranked_documents.append(doc)
    return reranked_documents

web_search_tool = TavilySearch(
    max_results=5,
    search_depth="advanced",
    include_answer=True,
    tavily_api_key=tavily_api_key
)

class GraphState(TypedDict):
    """
    Graph state is a dictionary that contains information we want to propagate to, and modify in, each graph node.
    """
    question: str
    original_question: str
    generation: str
    check: str
    datasource: str
    hallucination_checker_attempts: int
    answer_verifier_attempts: int
    documents: List[str]
    checker_result: str
    student_id: str

def document_retriever(state):
    print("\n---QUERY TRANSLATION AND RAG-FUSION---")
    question = state["question"]
    # Generate multiple query variants
    multi_query_generator = (
        multi_query_generation_prompt
        | llm_fast
        | StrOutputParser()
        | (lambda x: x.split("\n"))
    )
    queries = multi_query_generator.invoke({
        "question": question,
        "num_queries": 3,
        "vectorstore_content_summary": vectorstore_content_summary
    })

    # Sequential retrieval (avoid concurrent DB hits)
    retriever = book_data_vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={'k': 3, 'fetch_k': 10, "lambda_mult": 0.5}
    )
    per_query_docs = []
    for q in queries:
        try:
            per_query_docs.append(retriever.invoke(q))
        except Exception:
            # Best-effort: skip failed sub-query to keep the run resilient
            continue

    rag_fusion_mmr_results = reciprocal_rank_fusion(per_query_docs)
    top_k_results = rag_fusion_mmr_results[:5]
    print(f"Total number of results after fusion: {len(rag_fusion_mmr_results)}, taking top 5.")
    formatted_doc_results = []
    for doc in top_k_results:
        if isinstance(doc.metadata, str):
            try:
                metadata = json.loads(doc.metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        else:
            metadata = doc.metadata if doc.metadata else {}
        metadata = {k: v for k, v in metadata.items() if k != 'rrf_score'}
        formatted_doc_results.append(Document(
            metadata=metadata,
            page_content=doc.page_content
        ))
    return {"documents": formatted_doc_results}

def answer_generator(state):
    print("\n---ANSWER GENERATION---")
    documents = state["documents"]
    original_question = state.get("original_question", 0)
    question = original_question if original_question != 0 else state["question"]
    
    chat_history_context = "No profile context available."
    try:
        from src.workflows.profile_analyzer import get_profile_text_summary
        student_id = state.get("student_id", "unknown")
        print(f"--- Retrieving learner profile for student: {student_id} ---")
        profile_text = get_profile_text_summary(student_id)
        if profile_text:
            chat_history_context = f"Student Learning Profile:\n{profile_text}"
            print("--- Retrieved learner profile text summary ---")
        else:
            print(f"--- No profile found for student_id: {student_id} ---")
    except Exception as e:
        print(f"--- Error retrieving learner profile: {e} ---")

    documents = [
        Document(metadata=doc["metadata"], page_content=doc["page_content"])
        if isinstance(doc, dict) else doc
        for doc in documents
    ]
    answer_generator_prompt = answer_generator_prompt_template.format(
        context=documents,
        question=question,
        chat_history_context=chat_history_context
    )
    answer_generation = llm_powerful.invoke(answer_generator_prompt)
    print("Answer generation has been generated.")
    return {"generation": _to_text(answer_generation.content)}

def web_search(state):
    print("\n---WEB SEARCH---")
    question = state["question"]
    documents = state.get("documents", [])
    web_results = web_search_tool.invoke(question)
    print(f"Web search results type: {type(web_results)}")
    print(f"Web search results: {web_results}")

    if isinstance(web_results, str):
        formatted_web_results = [{"metadata": {"title": "Web Search Results", "url": "N/A"}, "page_content": web_results}]
    elif isinstance(web_results, list) and len(web_results) > 0:
        if isinstance(web_results[0], dict) and "title" in web_results[0]:
            formatted_web_results = [
                {"metadata": {"title": result.get("title", "No title"), "url": result.get("url", "No URL")},
                 "page_content": result.get("content", result.get("snippet", "No content"))}
                for result in web_results
            ]
        else:
            formatted_web_results = [
                {"metadata": {"title": f"Result {i+1}", "url": "N/A"}, "page_content": str(result)}
                for i, result in enumerate(web_results)
            ]
    else:
        formatted_web_results = [{"metadata": {"title": "Web Search Results", "url": "N/A"}, "page_content": str(web_results)}]
    
    documents = [
        Document(metadata=doc["metadata"], page_content=doc["page_content"])
        if isinstance(doc, dict) else doc
        for doc in documents
    ]
    documents.extend(formatted_web_results)
    print(f"Total number of web search documents: {len(formatted_web_results)}")
    return {"documents": documents}

def chitter_chatter(state):
    print("\n---CHIT-CHATTING---")
    question = state["question"]
    chitterchatter_prompt = chitterchatter_prompt_template.format(
        relevant_scope=relevant_scope,
        question=question,
    )
    chitterchatter_response = llm_fast.invoke([SystemMessage(chitterchatter_prompt), HumanMessage(question)])
    return {"generation": _to_text(chitterchatter_response.content)}

def query_rewriter(state):
    print("\n---QUERY REWRITE---")
    original_question = state.get("original_question", 0)
    question = original_question if original_question != 0 else state["question"]
    generation = state["generation"]
    query_rewriter_prompt = query_rewriter_prompt_template.format(
        question=question,
        generation=generation,
        vectorstore_content_summary=vectorstore_content_summary
    )
    query_rewriter_result = llm_fast.with_structured_output(method="json_mode").invoke(query_rewriter_prompt)
    return {"question": query_rewriter_result['rewritten_question'], "original_question": question}

def hallucination_checker_tracker(state):
    num_attempts = state.get("hallucination_checker_attempts", 0)
    return {"hallucination_checker_attempts": num_attempts + 1}

def answer_verifier_tracker(state):
    num_attempts = state.get("answer_verifier_attempts", 0)
    return {"answer_verifier_attempts": num_attempts + 1}

def route_question(state):
    print("---ROUTING QUESTION---")
    question = state["question"]
    query_router_prompt = query_router_prompt_template.format(
        relevant_scope=relevant_scope,
        vectorstore_content_summary=vectorstore_content_summary,
        question=question,
    )
    route_question_response = llm_fast.with_structured_output(method="json_mode").invoke(
        [SystemMessage(query_router_prompt), HumanMessage(question)]
    )
    parsed_router_output = route_question_response["Datasource"]
    print(f"---ROUTING QUESTION TO: {parsed_router_output}---")
    if parsed_router_output == "Websearch":
        return "Websearch"
    elif parsed_router_output == "Vectorstore":
        return "Vectorstore"
    elif parsed_router_output in ["Simple-FAQ", "Chitter-Chatter"]:
        return "Chitter-Chatter"
    else:
        # Fallback for safety
        return "Chitter-Chatter" 
async def grade_documents_parallel(state):
    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]
    
    async def grade_document(doc, question):
        relevance_grader_prompt = relevance_grader_prompt_template.format(document=doc, question=question)
        return await llm_fast.with_structured_output(method="json_mode").ainvoke(relevance_grader_prompt)
    
    tasks = [grade_document(doc, question) for doc in documents]
    results = await asyncio.gather(*tasks)
    
    filtered_docs = []
    for i, score in enumerate(results):
        if score["binary_score"].lower() == "pass":
            print(f"---GRADE: DOCUMENT RELEVANT--- {score['binary_score']}")
            filtered_docs.append(documents[i])
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
    
    total_docs = len(documents)
    relevant_docs = len(filtered_docs)
    
    if total_docs > 0:
        filtered_out_percentage = (total_docs - relevant_docs) / total_docs
        checker_result = "fail" if filtered_out_percentage >= 0.3 else "pass"
        print(f"---FILTERED OUT {filtered_out_percentage*100:.1f}% OF IRRELEVANT DOCUMENTS---")
        print(f"---**{checker_result}**---")
    else:
        checker_result = "fail"
        print("---NO DOCUMENTS AVAILABLE, WEB SEARCH TRIGGERED---")
    
    return {"documents": filtered_docs, "checker_result": checker_result}

def decide_to_generate_or_assess(state):
    """
    Determines the next step after document relevance grading.
    - If grading passed, proceeds to generate an answer.
    - If grading failed, assesses the original question to decide whether to
      try a web search or route to a simple FAQ handler.
    """
    print("---CHECK GENERATION CONDITION---")
    checker_result = state["checker_result"]

    # If relevance grading passed, proceed to generate an answer
    if checker_result == "pass":
        print("---DECISION: GENERATE---")
        return "generate"

    # If relevance grading failed, assess the question before proceeding
    print("---DECISION: Retrieval failed. Assessing question type before proceeding.---")
    original_question = state.get("original_question") or state.get("question", "")
    
    # Heuristic to check for simple FAQ-style questions
    faq_keywords = ["who", "what", "when", "where"]
    question_starts_with_faq_word = any(original_question.lower().strip().startswith(keyword) for keyword in faq_keywords)

    if question_starts_with_faq_word:
        print("---FAILURE ASSESSMENT: Question appears to be a simple FAQ. Re-routing to Chitter-Chatter.---")
        return "Chitter-Chatter"
    else:
        print("---FAILURE ASSESSMENT: Question is complex. Proceeding to Web Search.---")
        return "Websearch"

def check_generation_vs_documents_and_question(state):
    print("---CHECK HALLUCINATIONS WITH DOCUMENTS---")
    question = state.get("original_question", state["question"])
    documents = state["documents"]
    generation = state["generation"]
    hallucination_checker_attempts = state.get("hallucination_checker_attempts", 0)
    answer_verifier_attempts = state.get("answer_verifier_attempts", 0)

    hallucination_checker_prompt = hallucination_checker_prompt_template.format(documents=documents, generation=generation)
    hallucination_checker_result = llm_fast.with_structured_output(method="json_mode").invoke(hallucination_checker_prompt)
    
    def ordinal(n):
        return f"{n}{'th' if 10 <= n % 100 <= 20 else {1:'st', 2:'nd', 3:'rd'}.get(n % 10, 'th')}"

    if hallucination_checker_result['binary_score'].lower() == "pass":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        print("---VERIFY ANSWER WITH QUESTION---")
        answer_verifier_prompt = answer_verifier_prompt_template.format(question=question, generation=generation)
        answer_verifier_result = llm_fast.with_structured_output(method="json_mode").invoke(answer_verifier_prompt)

        if answer_verifier_result['binary_score'].lower() == "pass":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            return "useful"
        elif answer_verifier_attempts > 1:
            print("---DECISION: MAX RETRIES REACHED---")
            return "max retries"
        else:
            print(f"---DECISION: GENERATION DOES NOT ADDRESS QUESTION, RE-WRITE QUERY---")
            print(f"This is the {ordinal(answer_verifier_attempts+1)} attempt.")
            return "not useful"
    elif hallucination_checker_attempts > 1:
        print("---DECISION: MAX RETRIES REACHED---")
        return "max retries"
    else:
        print(f"---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        print(f"This is the {ordinal(hallucination_checker_attempts+1)} attempt.")
        return "not supported"

workflow = StateGraph(GraphState)

workflow.add_node("WebSearcher", web_search)
workflow.add_node("DocumentRetriever", document_retriever)
workflow.add_node("RelevanceGrader", grade_documents_parallel)
workflow.add_node("AnswerGenerator", answer_generator)
workflow.add_node("QueryRewriter", query_rewriter)
workflow.add_node("ChitterChatter", chitter_chatter)
workflow.add_node("HallucinationCheckerFailed", hallucination_checker_tracker)
workflow.add_node("AnswerVerifierFailed", answer_verifier_tracker)

workflow.set_conditional_entry_point(
    route_question,
    {
        "Websearch": "WebSearcher",
        "Vectorstore": "DocumentRetriever",
        "Chitter-Chatter": "ChitterChatter",
    },
)

workflow.add_edge("DocumentRetriever", "RelevanceGrader")
workflow.add_edge("WebSearcher", "AnswerGenerator")
workflow.add_edge("HallucinationCheckerFailed", "AnswerGenerator")
workflow.add_edge("AnswerVerifierFailed", "QueryRewriter")
workflow.add_edge("QueryRewriter", "DocumentRetriever")
workflow.add_edge("ChitterChatter", END)

workflow.add_conditional_edges(
    "RelevanceGrader",
    decide_to_generate_or_assess,
    {
        "generate": "AnswerGenerator",
        "Websearch": "WebSearcher",
        "Chitter-Chatter": "ChitterChatter"
    },
)

workflow.add_conditional_edges(
    "AnswerGenerator",
    check_generation_vs_documents_and_question,
    {
        "not supported": "HallucinationCheckerFailed",
        "useful": END,
        "not useful": "AnswerVerifierFailed",
        "max retries": "ChitterChatter"
    },
)

def get_workflow():
    return workflow.compile()