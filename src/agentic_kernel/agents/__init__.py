"""Agent implementations for the Agentic-Kernel system."""

# Import from new core modules for backward compatibility
from .core.base_agent import BaseAgent, AgentCapabilities, TaskCapability
from .core.message_handling import MessageHandlingMixin
from .core.consensus import ConsensusMixin
from .core.feedback import FeedbackMixin
from .core.enhanced_agent import EnhancedAgent, SimpleEnhancedAgent

# Import specific agent implementations
from .coder import CoderAgent
from .terminal import TerminalAgent
from .file_surfer import FileSurferAgent
from .web_surfer import WebSurferAgent
from .chat_agent import ChatAgent
from .memory_agent import MemoryAgent
from .orchestrator_agent import OrchestratorAgent

# Core components
__all__ = [
    # Base agent components
    "BaseAgent",
    "AgentCapabilities",
    "TaskCapability",

    # Mixins
    "MessageHandlingMixin",
    "ConsensusMixin",
    "FeedbackMixin",

    # Enhanced agent implementations
    "EnhancedAgent",
    "SimpleEnhancedAgent",

    # Specific agent implementations
    "CoderAgent",
    "TerminalAgent",
    "FileSurferAgent",
    "WebSurferAgent",
    "ChatAgent",
    "MemoryAgent",
    "OrchestratorAgent",
]
