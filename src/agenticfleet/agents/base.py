"""Base agent implementation for AgenticFleet."""

from typing import Optional

from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    model: str
    endpoint: str
    description: Optional[str] = None
    system_message: Optional[str] = None


class BaseAgent:
    """Base class for all agents in AgenticFleet."""
    
    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration."""
        self.config = config
        self.name = config.name
    
    async def handle_message(self, message: str) -> str:
        """Handle an incoming message. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement handle_message")
