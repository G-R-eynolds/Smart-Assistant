import streamlit as st
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.schema.messages import HumanMessage, AIMessage
import google.generativeai as genai

# Try to import the new langchain_chroma package, fall back to legacy if not available
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# Configure Streamlit page
st.set_page_config(
    page_title="AI Smart Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables from .env file
load_dotenv()

# Load required environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Load configurable performance parameters from .env with defaults
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "models/embedding-001")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.7"))
DB_DIRECTORY = os.getenv("DB_DIRECTORY", "db")

# Validate environment variables
if not GEMINI_API_KEY:
    st.error(
        "⚠️ GEMINI_API_KEY not found! Please check your .env file configuration."
    )
    st.info(
        """
        **Required .env file setup:**
        
        Create a `.env` file in your project root directory with the following content:
        
        ```
        # Google Gemini API Key (Required)
        # Get your API key from: https://makersuite.google.com/app/apikey
        GEMINI_API_KEY=your_actual_api_key_here
        
        # Model Configuration (Optional - defaults provided)
        GEMINI_MODEL=gemini-2.0-flash-exp
        EMBEDDINGS_MODEL=models/embedding-001
        TEMPERATURE=0.7
        
        # Document Processing Configuration (Optional - defaults provided)
        CHUNK_SIZE=1000
        CHUNK_OVERLAP=200
        
        # Retrieval Configuration (Optional - defaults provided)
        RETRIEVAL_K=5
        SCORE_THRESHOLD=0.7
        DB_DIRECTORY=db
        ```
        
        **Instructions:**
        1. Visit https://makersuite.google.com/app/apikey
        2. Sign in with your Google account
        3. Create a new API key
        4. Copy the key and replace 'your_actual_api_key_here' in your .env file
        5. Save the .env file and restart the application
        """
    )
    st.stop()

# Configuration successful
st.success("✅ Environment variables loaded successfully!")

# Display configuration info
with st.expander("🔧 Current Configuration", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Model Settings:**")
        st.write(f"• Gemini Model: `{GEMINI_MODEL}`")
        st.write(f"• Embeddings Model: `{EMBEDDINGS_MODEL}`")
        st.write(f"• Temperature: `{TEMPERATURE}`")
        
    with col2:
        st.write("**Processing Settings:**")
        st.write(f"• Chunk Size: `{CHUNK_SIZE}`")
        st.write(f"• Chunk Overlap: `{CHUNK_OVERLAP}`")
        st.write(f"• Retrieval K: `{RETRIEVAL_K}`")
        st.write(f"• Score Threshold: `{SCORE_THRESHOLD}` *(applied post-retrieval)*")
        st.write(f"• Database Directory: `{DB_DIRECTORY}`")

# Initialize Gemini AI models
@st.cache_resource
def initialize_ai_models():
    """
    Initialize and cache Gemini AI models for chat and embeddings.
    
    Returns:
        tuple: (chat_model, embeddings_model, native_chat_model)
    """
    try:
        # Configure Google Generative AI
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Initialize LangChain Gemini chat model for RAG chain
        chat_model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=TEMPERATURE,
            convert_system_message_to_human=True
        )
        
        # Initialize Gemini embeddings model
        embeddings_model = GoogleGenerativeAIEmbeddings(
            model=EMBEDDINGS_MODEL,
            google_api_key=GEMINI_API_KEY
        )
        
        # Initialize native Gemini chat model for conversation history
        native_chat_model = genai.GenerativeModel(GEMINI_MODEL)
        
        st.success("✅ AI models initialized successfully!")
        return chat_model, embeddings_model, native_chat_model
        
    except Exception as e:
        st.error(f"Failed to initialize AI models: {str(e)}")
        st.stop()

# Initialize models
chat_model, embeddings_model, native_chat_model = initialize_ai_models()

# Load persistent vector store
@st.cache_resource
def load_vector_store():
    """
    Load the persistent ChromaDB vector store from the configured directory.
    
    Returns:
        Chroma: Loaded vector store instance or None if not found
    """
    try:
        # Check if the database directory exists
        if not os.path.exists(DB_DIRECTORY):
            st.warning(f"📂 Vector store directory '{DB_DIRECTORY}' not found. Please run the ingest script first to create the database.")
            return None
        
        # Load the existing vector store
        vector_store = Chroma(
            persist_directory=DB_DIRECTORY,
            embedding_function=embeddings_model
        )
        
        # Get collection info to verify it's properly loaded
        collection = vector_store._collection
        doc_count = collection.count()
        
        if doc_count > 0:
            st.success(f"✅ Vector store loaded successfully! Found {doc_count} documents in the database.")
            return vector_store
        else:
            st.warning("📄 Vector store is empty. Please run the ingest script to add documents.")
            return None
            
    except Exception as e:
        st.error(f"❌ Failed to load vector store: {str(e)}")
        st.info("💡 Make sure you've run the ingest script first to create the vector database.")
        return None

# Load vector store
vector_store = load_vector_store()

# Create retriever from vector store
@st.cache_resource
def create_retriever(_vector_store):
    """
    Create a retriever from the ChromaDB vector store for document retrieval.
    
    Args:
        _vector_store (Chroma): The loaded vector store instance
        
    Returns:
        VectorStoreRetriever: Configured retriever or None if vector store is unavailable
    """
    if _vector_store is None:
        st.info("🔍 Retriever not available - vector store not loaded.")
        return None
    
    try:
        # Create retriever with configurable search parameters
        retriever = _vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": RETRIEVAL_K,  # Retrieve top K most relevant documents
            }
        )
        
        st.success("🔍 Document retriever created successfully!")
        return retriever
        
    except Exception as e:
        st.error(f"❌ Failed to create retriever: {str(e)}")
        return None

# Initialize retriever
retriever = create_retriever(vector_store)

# Create optimized retrieval chain using LCEL with native Gemini chat
@st.cache_resource
def create_optimized_retrieval_chain(_chat_model, _retriever):
    """
    Create an optimized RAG chain that uses Gemini's native chat for history management.
    
    Args:
        _chat_model: The LangChain Gemini chat model for RAG
        _retriever: The document retriever
        
    Returns:
        RunnableSequence: The optimized RAG chain or None if components unavailable
    """
    if _chat_model is None or _retriever is None:
        st.info("🔗 RAG chain not available - missing required components.")
        return None
    
    try:
        # Simplified prompt template for RAG without chat history handling
        answer_template = """You are an AI assistant helping users understand documents. 
        Use the following pieces of retrieved context to answer the question. 
        If you don't know the answer based on the context, just say that you don't know. 
        Keep the answer concise but comprehensive.

        Context:
        {context}

        Question: {question}
        
        Answer:"""
        
        answer_prompt = ChatPromptTemplate.from_template(answer_template)
        
        # Helper function to format retrieved documents
        def format_docs(docs):
            return "\n\n".join([doc.page_content for doc in docs])
        
        # Create simplified RAG chain (no chat history processing needed)
        rag_chain = (
            {
                "context": lambda x: format_docs(_retriever.invoke(x["question"])),
                "question": lambda x: x["question"]
            }
            | answer_prompt
            | _chat_model
            | StrOutputParser()
        )
        
        st.success("🔗 Optimized RAG chain created successfully!")
        return rag_chain
        
    except Exception as e:
        st.error(f"❌ Failed to create optimized RAG chain: {str(e)}")
        return None

# Initialize optimized RAG chain
rag_chain = create_optimized_retrieval_chain(chat_model, retriever)

# Update .env file with configuration template
@st.cache_data
def update_env_template():
    """
    Update the .env file with configuration template and current values.
    This creates a comprehensive .env template for users.
    """
    env_content = f"""# Google Gemini API Key (Required)
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY={GEMINI_API_KEY}

# Model Configuration (Optional - defaults provided)
GEMINI_MODEL={GEMINI_MODEL}
EMBEDDINGS_MODEL={EMBEDDINGS_MODEL}
TEMPERATURE={TEMPERATURE}

# Document Processing Configuration (Optional - defaults provided)
CHUNK_SIZE={CHUNK_SIZE}
CHUNK_OVERLAP={CHUNK_OVERLAP}

# Retrieval Configuration (Optional - defaults provided)
RETRIEVAL_K={RETRIEVAL_K}
SCORE_THRESHOLD={SCORE_THRESHOLD}
DB_DIRECTORY={DB_DIRECTORY}
"""
    
    # Only write if file doesn't already contain all these parameters
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                current_content = f.read()
                # Check if all parameters are present
                required_params = ['GEMINI_MODEL', 'EMBEDDINGS_MODEL', 'TEMPERATURE', 
                                 'CHUNK_SIZE', 'CHUNK_OVERLAP', 'RETRIEVAL_K', 
                                 'SCORE_THRESHOLD', 'DB_DIRECTORY']
                if not all(param in current_content for param in required_params):
                    with open('.env.template', 'w') as f:
                        f.write(env_content)
                    st.info("📝 Created .env.template with all configuration options")
    except Exception as e:
        st.warning(f"Could not create .env template: {e}")

# Call the template update function
update_env_template()

# Main application header
st.title("🤖 AI Smart Assistant")
st.markdown(
    """
    Welcome to your intelligent document assistant! Upload PDFs, ask questions, 
    and get instant answers powered by Google's Gemini AI.
    """
)

# Initialize chat session in session state
if "chat_session" not in st.session_state:
    # Initialize Gemini chat session with system instruction
    st.session_state.chat_session = native_chat_model.start_chat(
        history=[],
        # System instruction to set the assistant's behavior
    )
    st.session_state.chat_session.send_message(
        "You are an AI Smart Assistant that helps users understand documents. "
        "When provided with document context, use it to answer questions accurately. "
        "If you don't know something based on the available context, say so honestly. "
        "Be helpful, concise, and professional."
    )

# Initialize display messages for UI (separate from Gemini's internal history)
if "display_messages" not in st.session_state:
    st.session_state.display_messages = [
        {
            "role": "assistant",
            "content": "Hello! I'm your AI Smart Assistant. I can help you analyze documents and answer questions. How can I assist you today?"
        }
    ]

# Display chat message history
st.subheader("💬 Chat")
chat_container = st.container()

with chat_container:
    for message in st.session_state.display_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about your documents..."):
    # Add user message to display history
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate response using optimized approach
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                if rag_chain is not None and retriever is not None:
                    # Get relevant documents for the question with score filtering (using new invoke method)
                    relevant_docs = retriever.invoke(prompt)
                    
                    # Apply score threshold filtering manually if needed
                    if SCORE_THRESHOLD < 1.0 and hasattr(retriever, 'vectorstore'):
                        try:
                            # Use similarity_search_with_score for threshold filtering
                            docs_with_scores = retriever.vectorstore.similarity_search_with_score(
                                prompt, k=RETRIEVAL_K
                            )
                            # Filter by score threshold (lower scores are better in some implementations)
                            relevant_docs = [doc for doc, score in docs_with_scores if score >= SCORE_THRESHOLD]
                        except Exception:
                            # Fallback to regular retrieval if scoring fails
                            relevant_docs = retriever.invoke(prompt)
                    
                    if relevant_docs:
                        # Format context from retrieved documents
                        context = "\n\n".join([doc.page_content for doc in relevant_docs])
                        
                        # Create enhanced prompt with document context
                        enhanced_prompt = f"""Based on the following document context, please answer the user's question:

Document Context:
{context}

User Question: {prompt}

Please provide a helpful and accurate answer based on the document context. If the context doesn't contain enough information to answer the question, please say so."""
                        
                        # Use Gemini's native chat session (handles conversation history automatically)
                        response = st.session_state.chat_session.send_message(enhanced_prompt)
                        final_response = response.text
                    else:
                        # No relevant documents found, use general chat
                        response = st.session_state.chat_session.send_message(prompt)
                        final_response = f"I couldn't find relevant information in the documents for your question. However, I can provide general assistance: {response.text}"
                else:
                    # Fallback to general chat without document retrieval
                    response = st.session_state.chat_session.send_message(prompt)
                    final_response = f"Document retrieval is not available. General response: {response.text}"
                    
            except Exception as e:
                final_response = f"I apologize, but I encountered an error while processing your question: {str(e)}"
            
            st.markdown(final_response)
    
    # Add assistant response to display history
    st.session_state.display_messages.append({"role": "assistant", "content": final_response})