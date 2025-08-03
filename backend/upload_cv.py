#!/usr/bin/env python3
"""
CV Upload Helper Script

This script helps you quickly upload your CV PDF to the correct location
for the Smart Assistant job pipeline.
"""

import sys
import shutil
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python upload_cv.py <path_to_your_cv.pdf>")
        print("Example: python upload_cv.py ~/Downloads/my_cv.pdf")
        sys.exit(1)
    
    cv_source = Path(sys.argv[1])
    
    # Validate source file
    if not cv_source.exists():
        print(f"Error: CV file not found at {cv_source}")
        sys.exit(1)
    
    if cv_source.suffix.lower() != '.pdf':
        print(f"Error: File must be a PDF, got {cv_source.suffix}")
        sys.exit(1)
    
    # Set up destination
    backend_dir = Path(__file__).parent
    cv_dir = backend_dir / "data" / "cv"
    cv_destination = cv_dir / "cv.pdf"
    
    # Create directory if it doesn't exist
    cv_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup existing CV if it exists
    if cv_destination.exists():
        backup_path = cv_dir / f"cv_backup_{int(cv_destination.stat().st_mtime)}.pdf"
        shutil.copy2(cv_destination, backup_path)
        print(f"Backed up existing CV to: {backup_path}")
    
    # Copy new CV
    try:
        shutil.copy2(cv_source, cv_destination)
        print(f"✅ CV uploaded successfully!")
        print(f"   Source: {cv_source}")
        print(f"   Destination: {cv_destination}")
        print(f"   Size: {cv_destination.stat().st_size / 1024:.1f} KB")
        print()
        print("You can now:")
        print("1. Start the backend server: python -m app.main")
        print("2. Test CV loading: GET http://localhost:8080/api/smart-assistant/cv/info")
        print("3. Use /find_jobs command in the frontend to test the full pipeline")
        
    except Exception as e:
        print(f"Error copying CV file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
