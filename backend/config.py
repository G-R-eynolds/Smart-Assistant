"""
Configuration module for job search settings.
Provides Pydantic models and functions to save/load job search configuration.
"""

import json
import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field


class JobSearchConfig(BaseModel):
    """Pydantic model for job search configuration."""
    
    keywords: List[str] = Field(
        default=["Software Engineer"],
        description="List of job search keywords"
    )
    location: str = Field(
        default="United States",
        description="Job search location"
    )
    is_remote_only: bool = Field(
        default=False,
        description="Whether to search for remote jobs only"
    )


def get_config_path() -> Path:
    """Get the path to the job configuration file."""
    # Store config in the backend directory
    backend_dir = Path(__file__).parent
    return backend_dir / "job_config.json"


def save_config(config: JobSearchConfig) -> None:
    """
    Save the JobSearchConfig object as a JSON file.
    
    Args:
        config (JobSearchConfig): The configuration object to save
    """
    config_path = get_config_path()
    
    try:
        # Convert Pydantic model to dictionary, then to JSON
        config_data = config.model_dump()
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Configuration saved to {config_path}")
        
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        raise


def load_config() -> JobSearchConfig:
    """
    Load and parse job_config.json.
    If the file doesn't exist, return a default JobSearchConfig object.
    
    Returns:
        JobSearchConfig: The loaded or default configuration
    """
    config_path = get_config_path()
    
    # Check if config file exists
    if not config_path.exists():
        print(f"ℹ️  Config file not found at {config_path}, using defaults")
        # Return default configuration
        return JobSearchConfig(
            keywords=["Software Engineer", "Python Developer", "Full Stack Developer"],
            location="United States",
            is_remote_only=False
        )
    
    try:
        # Load and parse the JSON file
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Create JobSearchConfig from loaded data
        config = JobSearchConfig(**config_data)
        print(f"✅ Configuration loaded from {config_path}")
        return config
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON in {config_path}: {e}")
        print("ℹ️  Using default configuration")
        return JobSearchConfig()
        
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        print("ℹ️  Using default configuration")
        return JobSearchConfig()


def update_config(**kwargs) -> JobSearchConfig:
    """
    Update specific fields in the configuration.
    
    Args:
        **kwargs: Fields to update (keywords, location, is_remote_only)
        
    Returns:
        JobSearchConfig: The updated configuration
    """
    # Load current config
    current_config = load_config()
    
    # Update with provided kwargs
    config_dict = current_config.model_dump()
    config_dict.update(kwargs)
    
    # Create new config object
    updated_config = JobSearchConfig(**config_dict)
    
    # Save the updated config
    save_config(updated_config)
    
    return updated_config


def reset_config() -> JobSearchConfig:
    """
    Reset configuration to default values.
    
    Returns:
        JobSearchConfig: The default configuration
    """
    default_config = JobSearchConfig()
    save_config(default_config)
    print("🔄 Configuration reset to defaults")
    return default_config


def print_config() -> None:
    """Print the current configuration in a readable format."""
    config = load_config()
    
    print("\n📋 Current Job Search Configuration:")
    print("=" * 40)
    print(f"Keywords: {', '.join(config.keywords)}")
    print(f"Location: {config.location}")
    print(f"Remote Only: {'Yes' if config.is_remote_only else 'No'}")
    print("=" * 40)


# Example usage and testing
if __name__ == "__main__":
    print("🧪 Testing Job Search Configuration Module")
    print("=" * 50)
    
    # Test 1: Load default config
    print("\n1. Loading default configuration:")
    config = load_config()
    print(f"   Keywords: {config.keywords}")
    print(f"   Location: {config.location}")
    print(f"   Remote Only: {config.is_remote_only}")
    
    # Test 2: Save config
    print("\n2. Saving configuration:")
    save_config(config)
    
    # Test 3: Update config
    print("\n3. Updating configuration:")
    updated_config = update_config(
        keywords=["Data Scientist", "Machine Learning Engineer"],
        location="San Francisco, CA",
        is_remote_only=True
    )
    
    # Test 4: Print config
    print("\n4. Current configuration:")
    print_config()
    
    # Test 5: Reset config
    print("\n5. Resetting to defaults:")
    reset_config()
    print_config()
