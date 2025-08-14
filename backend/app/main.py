"""
Smart Assistant Backend API

Main FastAPI application for the Smart Assistant backend, integrating job discovery, 
inbox management, and intelligence briefing functionality.
"""
import asyncio
import logging
import os
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import core modules
from app.core.config import settings

# Import API routers
from app.api.smart_assistant import router as smart_assistant_router
from app.core.database import init_db, close_db
from app.core.graphrag_service import graphrag_service

# Setup logging
logger = logging.getLogger("smart_assistant")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database and other resources
    logger.info("Starting Smart Assistant Backend API")
    try:
        await init_db()
        # Start simple scheduler if configured
        try:
            graphrag_service.ensure_scheduler(settings.INDEX_SCHEDULE_INTERVAL_SECONDS)
        except Exception:
            logger.debug("scheduler_start_failed", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    yield
    
    # Shutdown: Close connections and cleanup
    logger.info("Shutting down Smart Assistant Backend API")
    try:
        await close_db()
    except Exception as e:
        logger.error(f"Failed to close database: {e}")

# Create FastAPI application
app = FastAPI(
    title="Smart Assistant API",
    description="API for Smart Assistant functionality including job discovery, inbox management, and intelligence briefing",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(smart_assistant_router, prefix="/api/smart-assistant", tags=["Smart Assistant"])

# Serve built frontend (Phase 1 graph viewer) if present
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(FRONTEND_DIST):
    # Mount the entire built SPA at /viewer for HTML history fallback
    app.mount("/viewer", StaticFiles(directory=FRONTEND_DIST, html=True), name="viewer")

    # Also mount the assets directory at /assets because Vite's default build
    # emits absolute references like /assets/index-xxxxx.js. Without this extra
    # mount requests to /assets/... 404 when the app is not hosted at root.
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve favicon if present to avoid noisy 404s
    favicon_path = os.path.join(FRONTEND_DIST, "favicon.ico")
    if os.path.isfile(favicon_path):
        @app.get("/favicon.ico")
        async def favicon():
            return FileResponse(favicon_path)

    @app.get("/viewer/index.html")
    async def viewer_index():
        index_path = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        raise HTTPException(status_code=404, detail="Viewer build not found")

    @app.get("/graph-viewer")
    async def graph_viewer_redirect():
        # Simple HTML pointing to SPA; could 301 redirect
        return HTMLResponse("""<html><head><meta http-equiv='refresh' content='0; url=/viewer/' /></head><body>Redirecting...</body></html>""")

# Open WebUI Compatible API Endpoints
@app.get("/api/config")
async def get_config():
    """Get backend configuration"""
    config = {
        "license_metadata": None,
        "status": True,
        "name": "Smart Assistant",
        "version": "0.1.0",  # Changed to a lower version to avoid "What's New" popup
        "default_locale": "en-US",
        "default_models": "",
        "default_prompt_suggestions": [],
        "images": {"enabled": False},
        "audio": {"enabled": False},
        "registration": {"enabled": True},
        "trusted_header_auth": False,
        "admin_details": {
            "name": "Admin",
            "email": "admin@smartassistant.com"
        },
        "features": {
            "auth": True,
            "auth_trusted_header": False,
            "enable_api_key": False,
            "enable_signup": True,
            "enable_login_form": True,
            "enable_web_search": False,
            "enable_google_drive_integration": False,
            "enable_onedrive_integration": False,
            "enable_image_generation": False,
            "enable_admin_export": False,
            "enable_admin_chat_access": False,
            "enable_community_sharing": False,
            "enable_autocomplete_generation": False,
            "enable_direct_connections": False,
            "enable_message_rating": False,
            "enable_websocket": False,
            "enable_version_update_check": False
        },
        "oauth": {"providers": {}},
        "default_user_role": "user",
        "ui": {}
    }
    print(f"Serving config: {config}")
    return config

@app.get("/api/models")
async def get_models_owui():
    """Open WebUI models endpoint - Returns available AI models"""
    return {
        "data": [
            {
                "id": "smart-assistant-job-pipeline",
                "name": "Smart Assistant Job Pipeline",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "smart-assistant"
            }
        ]
    }

@app.get("/api/version")
async def get_version():
    """Open WebUI version endpoint"""
    return {
        "version": "1.0.0"
    }

# Health check for Open WebUI compatibility
@app.get("/api/health")
async def health_check_api():
    """Health check endpoint"""
    return {"status": True}

async def get_current_user(authorization: str = Header(None)):
    """Get current user from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = authorization.replace("Bearer ", "")
    # Accept our mock token for testing
    if token == "mock-admin-token":
        return {
            "id": "mock-admin-id",
            "email": "admin@smartassistant.com",
            "name": "Admin User",
            "role": "admin"
        }
    
    # For demo purposes, return a mock user for any other token
    # In real implementation, you'd verify the JWT token
    return {
        "id": "user123",
        "email": "admin@smartassistant.com",
        "name": "Admin User",
        "role": "admin"
    }

# Auth endpoints

class SigninForm(BaseModel):
    email: str
    password: str

class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = ""

@app.post("/api/v1/auths/signin")
async def signin_post(form_data: SigninForm):
    """Open WebUI signin POST endpoint"""
    # For demo purposes, accept any credentials
    # In production, you'd validate against a real user database
    token = f"demo-token-{uuid4()}"
    
    return {
        "token": token,
        "token_type": "Bearer",
        "expires_at": int(time.time()) + 86400,  # 24 hours
        "id": str(uuid4()),
        "email": form_data.email,
        "name": form_data.email.split('@')[0].title(),
        "role": "admin" if form_data.email == "admin@smartassistant.com" else "user",
        "profile_image_url": ""
    }

@app.post("/api/v1/auths/signup")
async def signup_post(form_data: SignupForm):
    """Open WebUI signup POST endpoint"""
    token = f"demo-token-{uuid4()}"
    
    return {
        "token": token,
        "token_type": "Bearer", 
        "expires_at": int(time.time()) + 86400,  # 24 hours
        "id": str(uuid4()),
        "email": form_data.email,
        "name": form_data.name,
        "role": "user",
        "profile_image_url": form_data.profile_image_url or ""
    }

@app.get("/api/v1/auths/")
async def get_session_user(request: Request):
    """Get current session user info"""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.replace("Bearer ", "")
    
    # For demo purposes, return a mock user
    # In production, you'd validate the token and return real user data
    return {
        "id": "demo-user",
        "email": "user@smartassistant.com", 
        "name": "Demo User",
        "role": "admin",
        "profile_image_url": "",
        "permissions": {
            "chat": {
                "temporary_enforced": False
            }
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "app": "Smart Assistant Backend API",
        "version": "1.0.0",
        "status": "running",
    }

@app.post("/api/v1/auths/signout")
async def signout():
    """Sign out user"""
    return {"message": "Signed out successfully"}

@app.get("/api/v1/auths/signup/enabled")
async def get_signup_enabled(current_user: dict = Depends(get_current_user)):
    """Get signup enabled status"""
    return {"signup_enabled": True}

@app.post("/api/v1/auths/signup/enabled/toggle")
async def toggle_signup_enabled(current_user: dict = Depends(get_current_user)):
    """Toggle signup enabled status"""
    return {"signup_enabled": True}

@app.get("/api/v1/auths/signup/user/role")
async def get_default_user_role(current_user: dict = Depends(get_current_user)):
    """Get default user role for signup"""
    return {"role": "user"}

@app.post("/api/v1/auths/signup/user/role")
async def set_default_user_role(current_user: dict = Depends(get_current_user)):
    """Set default user role for signup"""
    return {"role": "user"}

# Chat endpoints for Open WebUI compatibility
@app.get("/api/v1/chats/")
async def get_chats(page: int = 1, current_user: dict = Depends(get_current_user)):
    """Get user chats with pagination"""
    return []

@app.get("/api/v1/chats/archived")
async def get_archived_chats(page: int = 1, order_by: str = "updated_at", direction: str = "desc"):
    """Get archived chats"""
    return []

@app.get("/api/v1/folders/")
async def get_folders(current_user: dict = Depends(get_current_user)):
    """Get user folders"""
    return []

@app.get("/api/v1/channels/")
async def get_channels(current_user: dict = Depends(get_current_user)):
    """Get user channels"""
    return []

# (Removed duplicate settings update endpoint)

@app.get("/api/v1/chats/pinned")
async def get_pinned_chats(current_user: dict = Depends(get_current_user)):
    """Get pinned chats"""
    return []

@app.get("/api/v1/configs/banners")
async def get_banners():
    """Get banner configurations"""
    return []

@app.get("/api/v1/chats/all/tags")
async def get_all_tags(current_user: dict = Depends(get_current_user)):
    """Get all chat tags"""
    return []

@app.get("/api/v1/tools/")
async def get_tools(current_user: dict = Depends(get_current_user)):
    """Get available tools"""
    return []

@app.get("/api/v1/users/user/settings")
async def get_user_settings(current_user: dict = Depends(get_current_user)):
    """Get user settings"""
    return {
        "ui": {
            "theme": "system",
            "language": "en-US",
            "showSettings": False,
            "showShortcuts": False,
            "showChangelog": False
        }
    }

@app.post("/api/v1/users/user/settings/update")
async def update_user_settings(settings_data: dict, current_user: dict = Depends(get_current_user)):
    """Update user settings"""
    return {"success": True}

@app.get("/api/changelog")
async def get_changelog():
    """Get changelog - return empty to prevent What's New popup"""
    return {"changelog": []}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Add missing endpoints for app initialization
@app.get("/api/v1/models")
async def get_models_v1():
    """Return available models (v1)"""
    return []

@app.get("/api/prompts")
async def get_prompts():
    """Return available prompts"""
    return []

@app.get("/api/v1/prompts")
async def get_prompts_v1():
    """Return available prompts (v1)"""
    return []

@app.get("/api/functions")
async def get_functions():
    """Return available functions"""
    return []

@app.get("/api/v1/functions")
async def get_functions_v1():
    """Return available functions (v1)"""
    return []

@app.get("/api/tools")
async def get_tools_public():
    """Return available tools"""
    return []

@app.get("/api/v1/tools")
async def get_tools_v1():
    """Return available tools (v1)"""
    return []

@app.get("/api/knowledge")
async def get_knowledge():
    """Return available knowledge bases"""
    return []

@app.get("/api/v1/knowledge")
async def get_knowledge_v1():
    """Return available knowledge bases (v1)"""
    return []

@app.get("/api/chats/tags")
async def get_chat_tags():
    """Return available chat tags"""
    return []

@app.get("/api/v1/chats/tags")
async def get_chat_tags_v1():
    """Return available chat tags (v1)"""
    return []

# (Removed duplicate banners endpoints; using the earlier definitions above)

# (Removed duplicate minimal user settings endpoint)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
