"""
src/agent package – Multi-Agent AI hỗ trợ học tập.

Public API:
  from src.agent import MainOrchestrator, PlanningAgent, BackgroundAgent, RegulationAgent
  from src.agent import create_orchestrator
  from src.agent.tools import init_tools, get_tool_schemas, execute_tool
  from src.agent.regulation_agent import init_regulation_agent, query_regulation, search_regulation
  from src.agent.worker import ReviewWorker, run_worker_once
"""

from .main_agent import MainOrchestrator, create_orchestrator
from .planning_agent import PlanningAgent
from .background_agent import BackgroundAgent
from .regulation_agent import RegulationAgent, init_regulation_agent, query_regulation, search_regulation
from .tools import init_tools, get_tool_schemas, execute_tool, AcademicTools
from .worker import ReviewWorker, WorkerConfig, NotificationPreference, run_worker_once
from .config import DEFAULT_MODEL

__all__ = [
    # Agents
    "MainOrchestrator",
    "create_orchestrator",
    "PlanningAgent",
    "BackgroundAgent",
    "RegulationAgent",
    # Tools
    "init_tools",
    "get_tool_schemas",
    "execute_tool",
    "AcademicTools",
    # Regulation
    "init_regulation_agent",
    "query_regulation",
    "search_regulation",
    # Worker
    "ReviewWorker",
    "WorkerConfig",
    "NotificationPreference",
    "run_worker_once",
    # Config
    "DEFAULT_MODEL",
]
