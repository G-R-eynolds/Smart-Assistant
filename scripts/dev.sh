#!/bin/bash
# Development script for running both frontend and backend

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Assistant Development Environment ===${NC}"

# Set environment variables
export CORS_ALLOW_ORIGIN=http://localhost:5173/
export PORT="${PORT:-8080}"
export HOST="${HOST:-0.0.0.0}"

# Start backend in background
echo -e "${YELLOW}Starting backend server...${NC}"
cd backend && ./dev.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${YELLOW}Starting frontend server...${NC}"
cd frontend && npm run dev &
FRONTEND_PID=$!

# Handle cleanup on script termination
function cleanup {
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
}
trap cleanup EXIT

# Keep script running
echo -e "${GREEN}Development environment started!${NC}"
echo -e "Frontend: http://localhost:5173"
echo -e "Backend: http://localhost:${PORT}"
echo -e "Press Ctrl+C to stop all servers"
wait
