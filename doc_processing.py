import os
import textwrap
import time
import unicodedata
from pprint import pprint

# Third-party imports
from dotenv import load_dotenv
from IPython.display import Markdown
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.firecrawl import FireCrawlLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from llama_cloud_services import LlamaParse
import nest_asyncio
from sqlalchemy.engine.url import make_url

# Load environment variables from .env file
load_dotenv()

connection_string = os.getenv("DB_CONNECTION")
openai_api_key = os.getenv("OPENAI_API_KEY")
llama_cloud_api_key =os.getenv("LLAMA_CLOUD_API_KEY")


# Quick check environment variables
if not os.getenv("OPENAI_API_KEY") or not os.getenv("DB_CONNECTION") or not os.getenv("LLAMA_CLOUD_API_KEY"):
    print(f"Error: Missing one or more required environment variables") # If so, print out your key to check
else:
    print("All environment variables loaded successfully")

# Initialize the embedding model
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

# Initialize the llm
llm = ChatOpenAI(temperature=0, 
                 model="gpt-4o", 
                 api_key=openai_api_key)

from langchain_pymupdf4llm import PyMuPDF4LLMLoader


handbook_data_dict_py = {}
for handbook in os.listdir('uploaded'):
    pdf_name = os.path.splitext(os.path.basename(handbook))[0]
    print(pdf_name)

    # Create a PyMuPDFLoader instance with the specified file path
    loader = PyMuPDF4LLMLoader(file_path = os.path.join("uploaded",handbook), 
                        mode='single')
    # Load data into Document objects
    docs = loader.load()
    handbook_data_dict_py[f'{pdf_name}'] = docs

    
from pprint import pprint
from langchain.schema import Document

handbook_data_dict_py_cleaned = {
    name: [Document(page_content = doc.page_content.replace("�", "ti"), 
                    metadata=doc.metadata)
           for doc in docs]
    for name, docs in handbook_data_dict_py.items()
}


# pprint(handbook_data_dict_py_cleaned['notes1'][0].metadata)

from langchain.schema import Document
from langchain_community.document_transformers.openai_functions import create_metadata_tagger
from langchain_openai import ChatOpenAI

schema = {
    "properties": {
        "title": {"type": "string", "description": "title of document"},    # Extracts the document title
        "description": {"type": "string", "description": "lab, syllabus, notes, requirements, definitions, discussion, rubric"},  # Extracts the type of document
        "topic": {"type": "string", "description": "keyword or subject of the document"}, # Extracts the topic of the document
        "source": {"type": "string", "description": "Creator or origin of the document"}, # Extracts the source of the document
        "date": {"type": "string", "description": "date of document"}, # Extracts the date of the document
    },
    "required": ["title","description","topic"] # Ensures that a title is always included
    
}

llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")  
document_tagger = create_metadata_tagger(metadata_schema=schema, llm=llm)

# Iterate through each document entry in the dictionary
for doc_key, item_list in handbook_data_dict_py_cleaned.items():
    print(f"Processing document: {doc_key}")

    try:
        # The document_tagger expects a list of Document objects
        # Pass the entire list of items for the current document to the tagger
        # The tagger returns a new list of documents with metadata added
        enhanced_item_list = document_tagger.transform_documents(item_list)

        # Replace the original list in the dictionary with the new list
        handbook_data_dict_py_cleaned[doc_key] = enhanced_item_list

        print(f"Finished tagging all items in document: {doc_key}")

    except Exception as e:
        print(f"  - Error processing document {doc_key}: {e}")
        # Handle any errors that occur during tagging for this document
# pprint(handbook_data_dict_py_cleaned['notes1'][0].metadata)

# Document-Specific Splitting
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

# Setup the Markdown header splitter
headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

# Create a new dictionary for the split documents
handbook_data_split = {}

for name, docs in handbook_data_dict_py_cleaned.items():
    split_docs = []
    for doc in docs:
        chunks = markdown_splitter.split_text(doc.page_content)
        split_docs.extend([
            Document(page_content=chunk.page_content, metadata=doc.metadata)
            for chunk in chunks
        ])
    handbook_data_split[name] = split_docs
handbook_data_split_values = [doc for docs in handbook_data_split.values() for doc in docs]

# Load new collection into PostgreSQL vector database
database_new = PGVector.from_documents(
    embedding = embedding_model,
    documents = handbook_data_split_values,        # The documents to be stored
    collection_name= "final_data",  # The new collection name in PostgreSQL
    connection=connection_string,   # Connection string to PostgreSQL
    pre_delete_collection=True,     # If True, delete the collection if it exists
    use_jsonb=True                  # Store metadata as JSONB for efficient querying
)

# Display confirmation message
print(f"Successfully loaded {len(handbook_data_split_values)} chunks.")