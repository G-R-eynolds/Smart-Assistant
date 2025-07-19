import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# Load environment variables
load_dotenv()


def initialize_gemini_embeddings():
    """
    Initialize Google Generative AI embeddings model.
    
    Returns:
        GoogleGenerativeAIEmbeddings: Configured embeddings model
        
    Raises:
        ValueError: If GEMINI_API_KEY is not found in environment variables
    """
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment variables. "
            "Please ensure it's set in your .env file."
        )
    
    try:
        # Configure the Google Generative AI library
        genai.configure(api_key=api_key)
        
        # Initialize embeddings model
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )
        
        print("✓ Gemini embeddings model initialized successfully")
        return embeddings
        
    except Exception as e:
        print(f"Error initializing Gemini embeddings: {str(e)}")
        raise


def load_pdf_files():
    """Load all PDF files from the 'data' directory."""
    data_dir = "data"
    documents = []
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        print(f"Directory '{data_dir}' not found.")
        return documents
    
    # Get all PDF files in the data directory
    pdf_files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in '{data_dir}' directory.")
        return documents
    
    # Load each PDF file
    for pdf_file in pdf_files:
        file_path = os.path.join(data_dir, pdf_file)
        print(f"Loading: {pdf_file}")
        
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            documents.extend(docs)
            print(f"Successfully loaded {len(docs)} pages from {pdf_file}")
        except Exception as e:
            print(f"Error loading {pdf_file}: {str(e)}")
    
    return documents


def split_documents_into_chunks(documents, chunk_size=1000, chunk_overlap=200):
    """
    Split documents into smaller chunks for efficient processing.
    
    Args:
        documents (list): List of loaded documents from PDFs
        chunk_size (int): Maximum size of each chunk in characters
        chunk_overlap (int): Number of overlapping characters between chunks
        
    Returns:
        list: List of document chunks
    """
    if not documents:
        print("No documents to split.")
        return []
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    print(f"Splitting {len(documents)} documents into chunks...")
    print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    
    try:
        chunks = text_splitter.split_documents(documents)
        print(f"Successfully created {len(chunks)} chunks")
        return chunks
    except Exception as e:
        print(f"Error splitting documents: {str(e)}")
        return []


def create_vector_store(chunks, embeddings_model, persist_directory="db"):
    """
    Create a persistent ChromaDB vector store with document chunks and embeddings.
    
    Args:
        chunks (list): List of document chunks to store
        embeddings_model: Configured embeddings model for generating vectors
        persist_directory (str): Directory path for persistent storage
        
    Returns:
        Chroma: Configured ChromaDB vector store instance
        
    Raises:
        Exception: If vector store creation fails
    """
    if not chunks:
        print("No chunks provided for vector store creation.")
        return None
    
    try:
        # Ensure the persist directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        print(f"Creating persistent vector store in '{persist_directory}'...")
        print(f"Processing {len(chunks)} document chunks...")
        
        # Create ChromaDB vector store with embeddings
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings_model,
            persist_directory=persist_directory
        )
        
        # Persist the vector store to disk
        vector_store.persist()
        
        print(f"✓ Vector store created successfully with {len(chunks)} chunks")
        print(f"✓ Data persisted to '{persist_directory}' directory")
        
        return vector_store
        
    except Exception as e:
        print(f"Error creating vector store: {str(e)}")
        raise


if __name__ == "__main__":
    # Initialize Gemini embeddings
    try:
        embeddings_model = initialize_gemini_embeddings()
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
    except Exception as e:
        print(f"Failed to initialize embeddings: {e}")
        exit(1)
    
    # Load PDF documents
    loaded_documents = load_pdf_files()
    print(f"\nTotal documents loaded: {len(loaded_documents)}")
    
    # Split documents into chunks
    document_chunks = split_documents_into_chunks(
        documents=loaded_documents,
        chunk_size=1000,
        chunk_overlap=200
    )
    print(f"Total chunks created: {len(document_chunks)}")
    
    # Create and populate vector store
    if document_chunks:
        try:
            vector_store = create_vector_store(
                chunks=document_chunks,
                embeddings_model=embeddings_model,
                persist_directory="db"
            )
            print("\n✓ Document ingestion pipeline completed successfully!")
        except Exception as e:
            print(f"Failed to create vector store: {e}")
            exit(1)
    else:
        print("No document chunks available for vector store creation.")