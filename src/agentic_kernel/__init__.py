"""Agentic Kernel - A framework for building autonomous agent systems.

This package provides tools and abstractions for creating, managing, and orchestrating
autonomous agents in a flexible and extensible way.

Main Components:
- Agents: Base classes and implementations for different agent types
- Orchestration: Tools for managing agent workflows and interactions
- Plugins: Extensible plugin system for adding new capabilities
- Configuration: Flexible configuration system for agents and workflows
"""

from typing import List, Type

# Version info
__version__ = "0.2.0"
__author__ = "Qredence"
__license__ = "MIT"

# Core types
# Agent system
from .agents.base import BaseAgent

# Configuration
from .config.loader import ConfigLoader
from .config_types import AgentConfig, LLMMapping

# Ledgers for tracking
from .ledgers import ProgressLedger, TaskLedger
from .orchestrator.core import OrchestratorAgent
from .plugins.base import BasePlugin
from .types import Task, WorkflowStep

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core types
    "Task",
    "WorkflowStep",
    "AgentConfig",
    "LLMMapping",
    # Agent system
    "BaseAgent",
    "OrchestratorAgent",
    "BasePlugin",
    # Ledgers
    "TaskLedger",
    "ProgressLedger",
    # Configuration
    "ConfigLoader",
]
