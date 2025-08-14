#!/bin/bash
# Development server for unified Smart Assistant backend

set -euo pipefail

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Assistant Backend Development Server ===${NC}"

# Navigate to project root
cd "$(dirname "$0")"

# Prefer a Python 3.12 venv inside backend if present; otherwise fall back to .venv or repo root; create if missing
P312_VENV="$(pwd)/.venv312"
BACKEND_VENV="$(pwd)/.venv"
ROOT_VENV="/home/gabe/Documents/Agent Project 2.0/.venv"

if [ -d "$P312_VENV" ]; then
    VENV_PATH="$P312_VENV"
elif [ -d "$BACKEND_VENV" ]; then
    VENV_PATH="$BACKEND_VENV"
elif [ -d "$ROOT_VENV" ]; then
    VENV_PATH="$ROOT_VENV"
else
    echo -e "${YELLOW}No virtualenv found. Creating one at ${BACKEND_VENV}...${NC}"
    python3 -m venv "$BACKEND_VENV"
    VENV_PATH="$BACKEND_VENV"
fi

echo -e "${YELLOW}Activating virtual environment at ${VENV_PATH}...${NC}"
source "${VENV_PATH}/bin/activate"
VENV_PY="${VENV_PATH}/bin/python"
VENV_PIP="${VENV_PATH}/bin/pip"
UVICORN_BIN="${VENV_PATH}/bin/uvicorn"

# Validate venv pip points to this venv; if not, recreate
if ! "$VENV_PIP" -V 2>/dev/null | grep -q "$VENV_PATH"; then
    echo -e "${YELLOW}Venv appears inconsistent. Recreating at ${BACKEND_VENV}...${NC}"
    deactivate || true
    rm -rf "$BACKEND_VENV"
    python3 -m venv "$BACKEND_VENV"
    source "${BACKEND_VENV}/bin/activate"
    VENV_PATH="$BACKEND_VENV"
    VENV_PY="${VENV_PATH}/bin/python"
    VENV_PIP="${VENV_PATH}/bin/pip"
    UVICORN_BIN="${VENV_PATH}/bin/uvicorn"
fi

# Ensure dependencies are installed
echo -e "${YELLOW}Ensuring Python dependencies are installed...${NC}"
"${VENV_PY}" -m pip install --upgrade pip setuptools wheel >/dev/null
"${VENV_PIP}" install -e . >/dev/null
if [ ! -x "$UVICORN_BIN" ]; then
    "${VENV_PIP}" install uvicorn[standard] >/dev/null
fi

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo -e "${YELLOW}Creating .env from .env.template...${NC}"
        cp .env.template .env
    else
        echo -e "${YELLOW}Creating minimal .env...${NC}"
        cat > .env <<EOF
HOST=0.0.0.0
PORT=8080
DATABASE_URL=sqlite:///data/webui.db
ENABLE_GRAPHRAG=true
GRAPH_STORE=sqlite
EOF
    fi
fi

# Determine port (prefer .env PORT or 8080); if busy, fallback to 8081
PORT_IN_ENV=$(grep -E '^PORT=' .env | cut -d'=' -f2 | tr -d '\r' || true)
PORT_TO_USE=${PORT_IN_ENV:-8080}
if ss -ltn '( sport = :'"$PORT_TO_USE"' )' | grep -q ":$PORT_TO_USE"; then
    echo -e "${YELLOW}Port ${PORT_TO_USE} is busy; falling back to 8081...${NC}"
    PORT_TO_USE=8081
fi

# Run the development server
echo -e "${GREEN}Starting development server on http://0.0.0.0:${PORT_TO_USE} ...${NC}"
"${UVICORN_BIN}" app.main:app --reload --host 0.0.0.0 --port "${PORT_TO_USE}"

# Deactivate virtual environment on exit
deactivate
