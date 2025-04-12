"""Base agent and utility classes for ADK multi-agent system."""

from typing import Any, Dict, List, Optional

class Agent:
    """Base Agent class with common functionality."""
    
    def __init__(self, name: str, model: str, instruction: str):
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

class InMemorySessionService:
    """In-memory session service for managing agent sessions."""
    
    def create_session(self, state: Dict, app_name: str, user_id: str):
        return {"state": state, "app_name": app_name, "user_id": user_id}

class FunctionTool:
    """Function tool wrapper for agent capabilities."""
    
    def __init__(self, name: str, description: str, function: callable):
        self.name = name
        self.description = description
        self.function = function 