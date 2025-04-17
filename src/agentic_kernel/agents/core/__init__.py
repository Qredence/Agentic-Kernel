"""
Core agent components for the Agentic Kernel.

This package contains the core components for building agents in the
Agentic Kernel, including the base agent class, mixins for various
functionality, and enhanced agent implementations.
"""

from .base_agent import AgentCapabilities, BaseAgent, TaskCapability
from .consensus import ConsensusMixin
from .enhanced_agent import EnhancedAgent, SimpleEnhancedAgent
from .feedback import FeedbackMixin
from .message_handling import MessageHandlingMixin

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
]