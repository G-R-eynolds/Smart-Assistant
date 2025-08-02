#!/bin/bash
# Development server for unified Smart Assistant backend

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Assistant Backend Development Server ===${NC}"

# Navigate to project root
cd "$(dirname "$0")"

# Use the existing root virtual environment
VENV_PATH="/home/gabe/Documents/Agent Project 2.0/.venv-py312"
echo -e "${YELLOW}Using existing virtual environment at ${VENV_PATH}...${NC}"

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source "${VENV_PATH}/bin/activate"

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -e ".[dev]" aiohttp

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file from example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env file with your configuration.${NC}"
fi

# Run the development server
echo -e "${GREEN}Starting development server...${NC}"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Deactivate virtual environment on exit
deactivate
