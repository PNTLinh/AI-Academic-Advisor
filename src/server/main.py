"""
Adaptive Academic Advisor API – FastAPI entry point.

Routes:
  - /api/chat   : Agentic chat (if agent is available)
  - /api/*      : Panel data APIs (user status, roadmap, preferences, transcript)
  - /health     : Health-check
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__)

# ─── Lifespan (replaces deprecated @app.on_event) ───────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic."""
    # ── Startup ──
    # Ensure uploads directory exists
    uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    # Try to initialise agent tools (non-fatal if agent package has issues)
    try:
        from .app.dependencies import init_all_agents
        init_all_agents()
        logger.info("✅ Agent tools initialised successfully.")
    except Exception as e:
        logger.warning(f"⚠️ Agent init skipped (non-fatal): {e}")

    logger.info("🚀 Server started.")
    yield
    # ── Shutdown ──
    logger.info("Server shutting down.")


# ─── App ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Adaptive Academic Advisor API",
    version="1.0.0",
    description="Agent-first API: Chatbot supported academic planning.",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────
# In production, set ALLOWED_ORIGINS to things like "https://your-ui.vercel.app"
origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Root Endpoint ───────────────────────────────────────────────────────
@app.get("/", tags=["System"])
def root():
    """Root endpoint: return simple API info."""
    return {"message": "Welcome to Adaptive Academic Advisor API. Go to /docs for Swagger UI."}

# ─── Health check ────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Checks server status and database connectivity."""
    health = {"status": "ok", "database": "unknown"}
    try:
        from .app.dependencies import get_academic_tools
        tools = get_academic_tools()
        # Simple query to check if DB is alive
        result = tools.db.execute("SELECT 1", fetchall=False)
        health["database"] = "connected" if result else "no_data"
    except Exception as e:
        health["status"] = "error"
        health["database"] = f"error: {str(e)}"
    
    return health

# ─── Routers ─────────────────────────────────────────────────────────────
from .app.routes import chat, panels, academic, worker_api, auth, chat_history

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat_history.router, prefix="/api", tags=["Chat History"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(academic.router, prefix="/api", tags=["Academic"])
app.include_router(panels.router, prefix="/api", tags=["Panels"])
app.include_router(worker_api.router, prefix="/api/worker", tags=["Worker"])
