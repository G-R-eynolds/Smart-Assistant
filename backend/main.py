import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA

# Load environment variables
load_dotenv()

# Create FastAPI app instance
app = FastAPI(title="Smart Assistant API", version="1.0.0")

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for chat API
class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

# Initialize LangChain components
def initialize_rag_chain():
    """Initialize the RAG chain with Gemini models and ChromaDB."""
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Initialize Gemini LLM
    llm = GoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=api_key,
        temperature=0.7
    )
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    # Load the persistent vector store
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_directory = os.path.join(script_dir, "db")
    vector_store = Chroma(
        persist_directory=db_directory,
        embedding_function=embeddings
    )
    
    # Create retriever
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    
    # Create RetrievalQA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=False
    )
    
    return qa_chain

# Initialize the RAG chain
rag_chain = initialize_rag_chain()

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage) -> ChatResponse:
    """
    Handle chat messages and return AI responses using RAG.
    """
    try:
        # Invoke the RAG chain with the user's message
        result = rag_chain.invoke({"query": chat_message.message})
        
        # Extract the result text
        response_text = result.get("result", "I'm sorry, I couldn't process your request.")
        
        return ChatResponse(response=response_text)
    
    except Exception as e:
        # Handle errors gracefully
        return ChatResponse(response=f"I encountered an error: {str(e)}")