import os
import glob
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Load environment variables
load_dotenv()

def load_pdf_documents():
    """Load all PDF files from the data directory."""
    documents = []
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    
    for pdf_file in pdf_files:
        print(f"Loading {pdf_file}...")
        loader = PyPDFLoader(pdf_file)
        docs = loader.load()
        documents.extend(docs)
    
    print(f"Loaded {len(documents)} document pages from {len(pdf_files)} PDF files")
    return documents

def split_documents(documents):
    """Split documents into chunks using RecursiveCharacterTextSplitter."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Split documents into {len(chunks)} chunks")
    return chunks

def initialize_embeddings():
    """Initialize Gemini embeddings model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    print("Initialized Gemini embeddings model")
    return embeddings

def create_vector_store(chunks, embeddings):
    """Create a persistent vector store using ChromaDB."""
    db_directory = "db"
    
    # Create the db directory if it doesn't exist
    os.makedirs(db_directory, exist_ok=True)
    
    # Create the vector store
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=db_directory
    )
    
    print(f"Created vector store with {len(chunks)} document chunks in '{db_directory}' directory")
    return vector_store

def main():
    """Main function to orchestrate the document ingestion process."""
    print("Starting document ingestion process...")
    
    # Load PDF documents
    documents = load_pdf_documents()
    
    if not documents:
        print("No PDF documents found in the data directory")
        return
    
    # Split documents into chunks
    chunks = split_documents(documents)
    
    # Initialize embeddings
    embeddings = initialize_embeddings()
    
    # Create vector store
    vector_store = create_vector_store(chunks, embeddings)
    
    print("Document ingestion completed successfully!")

if __name__ == "__main__":
    main()