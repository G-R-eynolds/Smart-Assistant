"""
Job Analysis Tool
Provides intelligent job scoring and analysis by comparing job descriptions 
against the user's CV using LangChain and Gemini AI.
"""

import os
import json
from pathlib import Path
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma


def load_env_variables():
    """Load environment variables from the project root .env file if not already loaded."""
    if not os.getenv('GEMINI_API_KEY'):
        from dotenv import load_dotenv
        # Load from project root (one level up from this file)
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)


def get_rag_retriever():
    """Initialize and return the RAG retriever for fetching CV content."""
    # Ensure environment variables are loaded
    load_env_variables()
    
    # Get API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    # Load the persistent vector store
    script_dir = Path(__file__).parent
    db_directory = script_dir / "db"
    vector_store = Chroma(
        persist_directory=str(db_directory),
        embedding_function=embeddings
    )
    
    # Create and return retriever
    return vector_store.as_retriever(search_kwargs={"k": 5})


def analyze_and_score_job(job_description: str) -> dict:
    """
    Analyze and score a job description against the user's CV.
    
    Args:
        job_description (str): The job description text to analyze
        
    Returns:
        dict: JSON object with score, priority, and summary
    """
    try:
        # Ensure environment variables are loaded
        load_env_variables()
        
        # Get API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # First use the RAG retriever to fetch the user's CV text
        retriever = get_rag_retriever()
        
        # Query for CV/resume content
        cv_query = "CV resume education experience skills qualifications background"
        cv_documents = retriever.invoke(cv_query)
        
        # Combine retrieved CV content
        cv_text = ""
        if cv_documents:
            cv_text = "\\n\\n".join([doc.page_content for doc in cv_documents])
        else:
            cv_text = "No CV information found in the knowledge base."
        
        # Define a detailed prompt template
        prompt_template = PromptTemplate(
            input_variables=["cv_text", "job_description"],
            template="""You are an expert career coach and recruitment specialist. Your task is to analyze how well a candidate's CV matches a specific job description.

CANDIDATE'S CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

Please perform a detailed comparison and analysis. Consider the following factors:
1. Skills alignment (technical and soft skills)
2. Experience relevance and level
3. Educational background match
4. Industry experience
5. Career progression alignment
6. Key requirements fulfillment

Based on your analysis, you must return a JSON object with exactly these three keys:

1. "score": An integer from 1-100 representing the match quality
   - 90-100: Excellent match, highly qualified
   - 75-89: Very good match, well qualified
   - 60-74: Good match, qualified with some gaps
   - 45-59: Fair match, qualified but missing key elements
   - 30-44: Poor match, significant gaps
   - 1-29: Very poor match, not suitable

2. "priority": A string indicating application priority
   - "High": Strong match, should apply immediately
   - "Medium": Good match, consider applying
   - "Low": Weak match, apply only if no better options

3. "summary": A brief 2-3 sentence explanation of the score, highlighting the main strengths and any significant gaps

Return ONLY the JSON object, no additional text or formatting:"""
        )
        
        # Initialize Gemini Chat LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=api_key,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        # Create a chain using the modern RunnableSequence pattern
        analysis_chain = prompt_template | llm
        
        # Invoke the chain with the job description and the retrieved CV text
        result = analysis_chain.invoke({
            "cv_text": cv_text,
            "job_description": job_description
        })
        
        # Extract the result text
        response_text = result.content.strip()
        
        # Parse the JSON output
        try:
            # Clean up the response text (remove any markdown formatting)
            clean_response = response_text.replace("```json", "").replace("```", "").strip()
            analysis_result = json.loads(clean_response)
            
            # Validate the required keys exist
            required_keys = ["score", "priority", "summary"]
            if not all(key in analysis_result for key in required_keys):
                raise ValueError(f"Missing required keys. Expected: {required_keys}")
            
            # Validate score is an integer between 1-100
            score = analysis_result["score"]
            if not isinstance(score, int) or not (1 <= score <= 100):
                raise ValueError("Score must be an integer between 1-100")
            
            # Validate priority is one of the expected values
            priority = analysis_result["priority"]
            if priority not in ["High", "Medium", "Low"]:
                raise ValueError("Priority must be 'High', 'Medium', or 'Low'")
            
            return analysis_result
            
        except (json.JSONDecodeError, ValueError) as parse_error:
            print(f"Error parsing LLM response: {parse_error}")
            print(f"Raw response: {response_text}")
            
            # Return a fallback result
            return {
                "score": 50,
                "priority": "Medium",
                "summary": f"Analysis completed but could not parse detailed results. Raw analysis available. Error: {str(parse_error)}"
            }
    
    except Exception as e:
        print(f"Error in job analysis: {e}")
        return {
            "score": 0,
            "priority": "Low",
            "summary": f"Error analyzing job: {str(e)}"
        }


def batch_analyze_jobs(job_descriptions: list) -> list:
    """
    Analyze multiple job descriptions at once.
    
    Args:
        job_descriptions (list): List of job description strings
        
    Returns:
        list: List of analysis results for each job
    """
    results = []
    
    for i, job_desc in enumerate(job_descriptions, 1):
        print(f"Analyzing job {i}/{len(job_descriptions)}...")
        analysis = analyze_and_score_job(job_desc)
        results.append(analysis)
    
    return results


def get_top_priority_jobs(job_analyses: list, min_score: int = 60) -> list:
    """
    Filter and sort job analyses to get top priority opportunities.
    
    Args:
        job_analyses (list): List of job analysis results
        min_score (int): Minimum score threshold
        
    Returns:
        list: Sorted list of high-priority job analyses
    """
    # Filter jobs above minimum score
    qualified_jobs = [job for job in job_analyses if job.get("score", 0) >= min_score]
    
    # Sort by score (highest first)
    sorted_jobs = sorted(qualified_jobs, key=lambda x: x.get("score", 0), reverse=True)
    
    return sorted_jobs


# Testing and example usage
def test_job_analysis():
    """Test the job analysis functionality with sample data."""
    print("🧪 Testing Job Analysis Tool")
    print("=" * 50)
    
    # Sample job description
    sample_job_description = """
    Senior Software Engineer - Python

    We are seeking a highly skilled Senior Software Engineer with expertise in Python development. 
    The ideal candidate will have 5+ years of experience building scalable web applications.

    Requirements:
    - Bachelor's degree in Computer Science or related field
    - 5+ years of professional Python development experience
    - Strong experience with Django or Flask frameworks
    - Proficiency in SQL databases (PostgreSQL, MySQL)
    - Experience with cloud platforms (AWS, GCP, Azure)
    - Knowledge of containerization (Docker, Kubernetes)
    - Strong problem-solving and communication skills
    - Experience with Agile development methodologies

    Responsibilities:
    - Design and develop high-quality software solutions
    - Collaborate with cross-functional teams
    - Mentor junior developers
    - Participate in code reviews and architectural decisions
    - Ensure code quality and best practices

    We offer competitive salary, excellent benefits, and opportunities for professional growth.
    """
    
    try:
        print("1. Testing single job analysis...")
        analysis = analyze_and_score_job(sample_job_description)
        
        print(f"   ✅ Analysis completed successfully")
        print(f"   📊 Score: {analysis['score']}/100")
        print(f"   🎯 Priority: {analysis['priority']}")
        print(f"   📝 Summary: {analysis['summary']}")
        
        return analysis
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None


if __name__ == "__main__":
    # Run test
    test_job_analysis()
