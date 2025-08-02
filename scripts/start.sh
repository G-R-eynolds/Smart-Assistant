#!/usr/bin/env bash
# Production startup script for the Smart Assistant application

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.." || exit

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Smart Assistant Production Startup ===${NC}"

# Check for .env file
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}Creating .env file from example...${NC}"
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}Please edit backend/.env with your production configuration.${NC}"
    exit 1
fi

# Environment variables
export PORT="${PORT:-8000}"
export HOST="${HOST:-0.0.0.0}"
export APP_ENV="production"

# Generate secret key if not provided
if [ -z "$WEBUI_SECRET_KEY" ]; then
    if [ -f ".webui_secret_key" ]; then
        export WEBUI_SECRET_KEY=$(cat .webui_secret_key)
    else
        echo -e "${YELLOW}Generating secret key...${NC}"
        export WEBUI_SECRET_KEY=$(openssl rand -hex 32)
        echo "$WEBUI_SECRET_KEY" > .webui_secret_key
    fi
fi

# Start the application
echo -e "${YELLOW}Starting production server...${NC}"
cd backend && python -m uvicorn app.main:app --host $HOST --port $PORT --workers 4

echo -e "${GREEN}Server started successfully!${NC}"
    echo $(head -c 12 /dev/random | base64) > "$KEY_FILE"
  fi

  echo "Loading WEBUI_SECRET_KEY from $KEY_FILE"
  WEBUI_SECRET_KEY=$(cat "$KEY_FILE")
fi

if [[ "${USE_OLLAMA_DOCKER,,}" == "true" ]]; then
    echo "USE_OLLAMA is set to true, starting ollama serve."
    ollama serve &
fi

if [[ "${USE_CUDA_DOCKER,,}" == "true" ]]; then
  echo "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# Check if SPACE_ID is set, if so, configure for space
if [ -n "$SPACE_ID" ]; then
  echo "Configuring for HuggingFace Space deployment"
  if [ -n "$ADMIN_USER_EMAIL" ] && [ -n "$ADMIN_USER_PASSWORD" ]; then
    echo "Admin user configured, creating"
    WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' &
    webui_pid=$!
    echo "Waiting for webui to start..."
    while ! curl -s http://localhost:8080/health > /dev/null; do
      sleep 1
    done
    echo "Creating admin user..."
    curl \
      -X POST "http://localhost:8080/api/v1/auths/signup" \
      -H "accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{ \"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\" }"
    echo "Shutting down webui..."
    kill $webui_pid
  fi

  export WEBUI_URL=${SPACE_HOST}
fi

PYTHON_CMD=$(command -v python3 || command -v python)

WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec "$PYTHON_CMD" -m uvicorn open_webui.main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' --workers "${UVICORN_WORKERS:-1}"
