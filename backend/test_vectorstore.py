import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Load environment variables
load_dotenv(dotenv_path="../.env")

# Get API key
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key found: {'Yes' if api_key else 'No'}")

# Initialize embeddings
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=api_key
)

# Load the vector store
db_directory = "db"
vector_store = Chroma(
    persist_directory=db_directory,
    embedding_function=embeddings
)

# Test the vector store
print(f"Vector store created successfully")

# Check if there are any documents
try:
    # Get collection info
    collection = vector_store._collection
    count = collection.count()
    print(f"Number of documents in vector store: {count}")
    
    if count > 0:
        # Test a simple query
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke("CV education experience")
        print(f"Retrieved {len(docs)} documents")
        for i, doc in enumerate(docs):
            print(f"Doc {i+1}: {doc.page_content[:200]}...")
    
except Exception as e:
    print(f"Error testing vector store: {e}")
