"""Agent implementations for the Agentic-Kernel system."""

from .base import BaseAgent
from .coder import CoderAgent
from .terminal import TerminalAgent
from .file_surfer import FileSurferAgent
from .web_surfer import WebSurferAgent
from .chat_agent import ChatAgent

__all__ = [
    "BaseAgent",
    "CoderAgent",
    "TerminalAgent",
    "FileSurferAgent",
    "WebSurferAgent",
    "ChatAgent",
]
