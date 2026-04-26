"""
Dependency injection helpers.

Provides singleton AcademicTools for route handlers via FastAPI Depends().
Agent initialisation is wrapped in try/except so the server still starts
even when the agent package has import issues (e.g. missing config).
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load .env early
load_dotenv()

# ── Ensure src/ is on sys.path for agent imports ──────────────────────────
_src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────
# Default to local 'data' dir, but allow override for Docker/Railway volumes
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))
REGULATIONS_DIR = os.getenv("REGULATIONS_DIR", os.path.join(DATA_DIR, "regulations"))
UPLOADS_DIR = os.getenv("UPLOADS_DIR", os.path.join(DATA_DIR, "uploads"))

# Database configuration - supports both PostgreSQL and SQLite
DB_URL = os.getenv("DATABASE_URL", "")
if DB_URL.startswith("postgresql://") or DB_URL.startswith("postgres://"):
    # PostgreSQL connection (Neon, Supabase, etc.)
    DATABASE_URL = DB_URL
    IS_POSTGRES = True
else:
    # Fallback to SQLite (local development)
    DB_PATH = DB_URL or os.path.join(DATA_DIR, "academic.db")
    DATABASE_URL = DB_PATH
    IS_POSTGRES = False

logger.info(f"Database mode: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")

# ── Singleton ────────────────────────────────────────────────────────────
_academic_tools = None


def get_academic_tools():
    """Return the shared AcademicTools instance (lazy init)."""
    global _academic_tools
    if _academic_tools is None:
        try:
            from src.agent.tools import AcademicTools
            _academic_tools = AcademicTools(DATABASE_URL)
        except Exception as e:
            logger.error(f"Failed to create AcademicTools: {e}")
            raise RuntimeError(
                f"AcademicTools could not be initialised. "
                f"Database mode: {'Postgres' if IS_POSTGRES else 'SQLite'}."
            )
    return _academic_tools


def init_all_agents():
    """Initialise agent tools at startup (best-effort)."""
    # 1. AcademicTools
    try:
        get_academic_tools()
    except Exception as e:
        logger.warning(f"AcademicTools init skipped: {e}")

    # 2. Regulation Agent
    try:
        if os.path.exists(REGULATIONS_DIR):
            from src.agent.regulation_agent import init_regulation_agent
            init_regulation_agent(regulations_dir=REGULATIONS_DIR)
            logger.info("RegulationAgent initialised.")
    except Exception as e:
        logger.warning(f"RegulationAgent init skipped: {e}")

    # 3. Uploads directory
    uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
