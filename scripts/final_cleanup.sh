#!/bin/bash
# Final cleanup script for the Smart Assistant project
# This script will remove old directories that are no longer needed
# after the refactoring and consolidation process.

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Assistant Project Cleanup ===${NC}"
echo -e "${YELLOW}This script will remove old directories that are no longer needed.${NC}"
echo -e "${RED}WARNING: This action cannot be undone. Make sure you have committed any changes.${NC}"
read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cleanup aborted.${NC}"
    exit 1
fi

echo -e "${YELLOW}Starting cleanup...${NC}"

# Define directories to remove
DIRS_TO_REMOVE=(
    "backend"
    "open-webui"
    "smart-assistant"
    "Spec"
)

# Define files to remove
FILES_TO_REMOVE=(
    "test_live_job_discovery.py"
    "test_phase1_simplified.py"
    "test_quick_job_discovery.py"
    "smart-assistant-microservice.py"
    "requirements.txt"
    "OPEN_WEBUI_INTEGRATION_PLAN.md"
)

# Remove directories
for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "Removing directory: ${YELLOW}$dir${NC}"
        rm -rf "$dir"
    else
        echo -e "Directory not found: ${RED}$dir${NC}"
    fi
done

# Remove files
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        echo -e "Removing file: ${YELLOW}$file${NC}"
        rm "$file"
    else
        echo -e "File not found: ${RED}$file${NC}"
    fi
done

echo -e "${GREEN}Cleanup completed successfully!${NC}"
echo -e "The project structure has been consolidated to:"
echo -e "  - ${BLUE}frontend/${NC}: SvelteKit frontend application"
echo -e "  - ${BLUE}backend/${NC}: FastAPI backend application"
echo -e "  - ${BLUE}docs/${NC}: Project documentation"
echo -e "  - ${BLUE}scripts/${NC}: Utility and build scripts"

# Rename new-backend to backend
if [ -d "new-backend" ]; then
    echo -e "${YELLOW}Renaming new-backend to backend...${NC}"
    if [ -d "backend" ]; then
        echo -e "${RED}ERROR: Cannot rename new-backend to backend because backend directory already exists.${NC}"
        echo -e "Please manually move content from new-backend to backend."
    else
        mv new-backend backend
        echo -e "${GREEN}Renamed successfully!${NC}"
    fi
fi

echo -e "${GREEN}Project cleanup is now complete!${NC}"
