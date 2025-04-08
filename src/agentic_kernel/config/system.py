"""System configuration module."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SystemConfig(BaseModel):
    """Configuration for the agent system."""

    name: str = Field(default="default", description="Name of the system")
    description: Optional[str] = Field(
        default=None, description="Description of the system"
    )
    max_agents: int = Field(
        default=10, description="Maximum number of agents allowed in the system"
    )
    max_tasks_per_agent: int = Field(
        default=5, description="Maximum number of tasks per agent"
    )
    task_timeout: int = Field(
        default=300, description="Default task timeout in seconds"
    )
    memory_retention_days: int = Field(
        default=7, description="Number of days to retain memory entries"
    )
    enable_logging: bool = Field(default=True, description="Enable system logging")
    log_level: str = Field(default="INFO", description="Logging level")

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
