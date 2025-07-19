import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from langchain.memory import ConversationBufferMemory
from config import load_config
from scraping_tool import scrape_page_content, parse_job_search_results, parse_job_description_page
from analysis_tool import analyze_and_score_job
import urllib.parse

# Load environment variables
load_dotenv(dotenv_path="../.env")

# Create FastAPI app instance
app = FastAPI(title="Smart Assistant API", version="1.0.0")

# In-memory storage for conversation sessions
conversation_sessions = {}

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
    session_id: str = "default"  # Default session for backward compatibility

class ChatResponse(BaseModel):
    response: str

# Pydantic models for conversation history
class QAPair(BaseModel):
    question: str
    answer: str

class ConversationHistory(BaseModel):
    conversations: list[QAPair]

class IngestResponse(BaseModel):
    message: str

class JobSearchResponse(BaseModel):
    processed_jobs: list
    total_found: int
    saved_count: int
    message: str

# Initialize LangChain components
def initialize_rag_chain():
    """Initialize the RAG chain with Gemini chat models and ChromaDB."""
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Initialize Gemini Chat LLM
    llm = ChatGoogleGenerativeAI(
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
    
    # Create ConversationalRetrievalChain (without memory - we'll manage that per session)
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        return_source_documents=False,
        verbose=False
    )
    
    return qa_chain

# Initialize the RAG chain
rag_chain = initialize_rag_chain()

def check_if_job_exists(job_url: str) -> bool:
    """
    Check if a job with the given URL already exists in the vector store.
    
    Args:
        job_url (str): The job URL to check for
        
    Returns:
        bool: True if job exists, False otherwise
    """
    try:
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Initialize embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Load the ChromaDB vector store
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_directory = os.path.join(script_dir, "db")
        vector_store = Chroma(
            persist_directory=db_directory,
            embedding_function=embeddings
        )
        
        # Use the get() method with a where filter to check if document exists
        results = vector_store.get(
            where={"source_url": job_url}
        )
        
        # Check if any documents were found
        if results and results.get('ids') and len(results['ids']) > 0:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error checking if job exists: {e}")
        return False

def get_conversation_memory(session_id: str) -> ConversationBufferMemory:
    """Get or create conversation memory for a session."""
    if session_id not in conversation_sessions:
        conversation_sessions[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    return conversation_sessions[session_id]

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_message: ChatMessage) -> ChatResponse:
    """
    Handle chat messages and return AI responses using RAG with conversation memory.
    """
    try:
        # Get conversation memory for this session
        memory = get_conversation_memory(chat_message.session_id)
        
        # Invoke the RAG chain with the user's message and conversation history
        result = rag_chain.invoke({
            "question": chat_message.message,
            "chat_history": memory.chat_memory.messages
        })
        
        # Extract the result text
        response_text = result.get("answer", "I'm sorry, I couldn't process your request.")
        
        # Save the conversation to memory
        memory.save_context(
            {"input": chat_message.message},
            {"output": response_text}
        )
        
        return ChatResponse(response=response_text)
    
    except Exception as e:
        # Handle errors gracefully
        return ChatResponse(response=f"I encountered an error: {str(e)}")

# Clear conversation endpoint
@app.post("/api/clear-session")
async def clear_session(session_data: dict):
    """Clear conversation memory for a session."""
    session_id = session_data.get("session_id", "default")
    if session_id in conversation_sessions:
        del conversation_sessions[session_id]
    return {"message": f"Session {session_id} cleared successfully"}

# Job search and analysis endpoint
@app.post("/api/jobs/run-search", response_model=JobSearchResponse)
async def run_job_search() -> JobSearchResponse:
    """
    Run automated job search, analysis, and storage workflow.
    """
    try:
        # First call load_config() to get the user's preferences
        config = load_config()
        
        # Construct the LinkedIn job search URL from the config
        base_url = "https://www.linkedin.com/jobs/search/"
        params = {
            "keywords": " ".join(config.keywords),
            "location": config.location
        }
        
        # Add remote filter if specified
        if config.is_remote_only:
            params["f_WT"] = "2"  # LinkedIn's remote work filter
        
        # Build the search URL
        search_url = base_url + "?" + urllib.parse.urlencode(params)
        
        print(f"🔍 Searching LinkedIn with URL: {search_url}")
        
        # Call await scrape_page_content() with the search URL
        search_page_html = await scrape_page_content(search_url)
        
        # Parse the job search results
        scraped_jobs = parse_job_search_results(search_page_html)
        
        if not scraped_jobs:
            return JobSearchResponse(
                processed_jobs=[],
                total_found=0,
                saved_count=0,
                message="No jobs found in search results"
            )
        
        print(f"📋 Found {len(scraped_jobs)} jobs in search results")
        
        # Initialize an empty list to hold the results
        processed_jobs = []
        saved_count = 0
        
        # Asynchronously loop through each scraped job
        for i, job in enumerate(scraped_jobs, 1):
            try:
                print(f"Processing job {i}/{len(scraped_jobs)}: {job['title']}")
                
                # Check if the job already exists
                job_exists = check_if_job_exists(job['url'])
                
                if job_exists:
                    print(f"   ⏭️  Job already exists, skipping...")
                    continue
                
                # Scrape the individual job description page
                print(f"   🔍 Scraping job description...")
                job_page_html = await scrape_page_content(job['url'])
                
                # Parse the job description
                job_description = parse_job_description_page(job_page_html)
                
                if not job_description or job_description == "No job description found":
                    print(f"   ⚠️  Could not extract job description, skipping...")
                    continue
                
                # Analyze and score the job
                print(f"   🧠 Analyzing job match...")
                analysis = analyze_and_score_job(job_description)
                
                # Create comprehensive job data
                job_data = {
                    **job,  # title, company, location, url
                    "description": job_description,
                    "analysis": analysis,
                    "config_used": {
                        "keywords": config.keywords,
                        "location": config.location,
                        "is_remote_only": config.is_remote_only
                    }
                }
                
                # Check if score is above threshold (70)
                score = analysis.get("score", 0)
                
                if score >= 70:
                    print(f"   ✅ High score ({score}/100), saving to systems...")
                    
                    # Save to ChromaDB with job URL in metadata
                    try:
                        # Get API key from environment
                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY not found in environment variables")
                        
                        # Initialize embeddings
                        embeddings = GoogleGenerativeAIEmbeddings(
                            model="models/embedding-001",
                            google_api_key=api_key
                        )
                        
                        # Load the ChromaDB vector store
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        db_directory = os.path.join(script_dir, "db")
                        vector_store = Chroma(
                            persist_directory=db_directory,
                            embedding_function=embeddings
                        )
                        
                        # Create document for the job
                        job_document = Document(
                            page_content=f"Job Title: {job['title']}\\n"
                                       f"Company: {job['company']}\\n"
                                       f"Location: {job['location']}\\n"
                                       f"Description: {job_description}\\n"
                                       f"Analysis Score: {score}/100\\n"
                                       f"Priority: {analysis.get('priority', 'Medium')}",
                            metadata={
                                "source": "linkedin_job",
                                "source_url": job['url'],
                                "job_title": job['title'],
                                "company": job['company'],
                                "location": job['location'],
                                "score": score,
                                "priority": analysis.get('priority', 'Medium'),
                                "type": "job_posting"
                            }
                        )
                        
                        # Add to vector store
                        vector_store.add_documents([job_document])
                        
                        job_data["saved_to_vectorstore"] = True
                        saved_count += 1
                        
                    except Exception as e:
                        print(f"   ⚠️  Error saving to vector store: {e}")
                        job_data["saved_to_vectorstore"] = False
                        job_data["vectorstore_error"] = str(e)
                
                else:
                    print(f"   📊 Score ({score}/100) below threshold, not saving...")
                    job_data["saved_to_vectorstore"] = False
                    job_data["reason_not_saved"] = f"Score ({score}) below threshold (70)"
                
                # Add to processed jobs list
                processed_jobs.append(job_data)
                
            except Exception as e:
                print(f"   ❌ Error processing job {job['title']}: {e}")
                error_job_data = {
                    **job,
                    "error": str(e),
                    "analysis": {"score": 0, "priority": "Low", "summary": f"Error processing: {str(e)}"},
                    "saved_to_vectorstore": False
                }
                processed_jobs.append(error_job_data)
                continue
        
        # Return the results
        return JobSearchResponse(
            processed_jobs=processed_jobs,
            total_found=len(scraped_jobs),
            saved_count=saved_count,
            message=f"Processed {len(scraped_jobs)} jobs, saved {saved_count} high-scoring opportunities"
        )
        
    except Exception as e:
        print(f"❌ Error in job search workflow: {e}")
        return JobSearchResponse(
            processed_jobs=[],
            total_found=0,
            saved_count=0,
            message=f"Error running job search: {str(e)}"
        )

# Conversation ingestion endpoint
@app.post("/api/ingest-conversation", response_model=IngestResponse)
async def ingest_conversation(conversation_history: ConversationHistory) -> IngestResponse:
    """
    Ingest conversation history into the vector store.
    """
    try:
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Initialize embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        # Load the ChromaDB vector store
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_directory = os.path.join(script_dir, "db")
        vector_store = Chroma(
            persist_directory=db_directory,
            embedding_function=embeddings
        )
        
        # Create LangChain Documents from Q&A pairs
        documents = []
        for qa_pair in conversation_history.conversations:
            # Format Q&A pair as a document
            content = f"Question: {qa_pair.question}\nAnswer: {qa_pair.answer}"
            doc = Document(
                page_content=content,
                metadata={
                    "source": "conversation_history",
                    "type": "qa_pair",
                    "question": qa_pair.question,
                    "answer": qa_pair.answer
                }
            )
            documents.append(doc)
        
        # Add documents to the vector store
        if documents:
            vector_store.add_documents(documents)
            return IngestResponse(
                message=f"Successfully ingested {len(documents)} Q&A pairs into the vector store"
            )
        else:
            return IngestResponse(message="No conversations provided to ingest")
    
    except Exception as e:
        return IngestResponse(message=f"Error ingesting conversations: {str(e)}")