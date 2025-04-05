"""Configuration classes for the Agentic-Kernel system."""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for an agent in the system.
    
    Attributes:
        name: The name of the agent
        model: The model to use (e.g., GPT-4)
        temperature: The temperature for model sampling
        max_tokens: Maximum tokens for model responses
        system_message: Optional system message for the agent
        extra_config: Additional configuration options
    """

    name: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    system_message: Optional[str] = None
    extra_config: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True 