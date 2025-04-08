"""Configuration classes for the Agentic-Kernel system."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class LLMMapping(BaseModel):
    """Configuration for LLM mapping.

    Attributes:
        model: The model to use (e.g., GPT-4)
        endpoint: The endpoint to use (e.g., azure_openai)
        temperature: The temperature for model sampling
        max_tokens: Maximum tokens for model responses
    """

    model: str
    endpoint: str
    temperature: float = 0.7
    max_tokens: int = 2000


class AgentConfig(BaseModel):
    """Configuration for an agent in the system.

    Attributes:
        name: The name of the agent
        type: The type of agent (e.g., chat, terminal, web_surfer)
        description: A description of the agent's capabilities
        llm_mapping: The LLM mapping configuration
        system_message: Optional system message for the agent
        extra_config: Additional configuration options
    """

    name: str
    type: str = Field(
        ..., description="The type of agent (e.g., chat, terminal, web_surfer)"
    )
    description: str = Field(
        ..., description="A description of the agent's capabilities"
    )
    llm_mapping: LLMMapping
    system_message: Optional[str] = None
    extra_config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class AgentTeamConfig(BaseModel):
    """Configuration for a team of agents.

    Attributes:
        name: The name of the team
        description: A description of the team
        agents: List of agent configurations
        orchestrator: Optional configuration for the orchestrator agent
        extra_config: Additional configuration options
    """

    name: str
    description: str
    agents: List[AgentConfig]
    orchestrator: Optional[AgentConfig] = None
    extra_config: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class DockerSandboxConfig(BaseModel):
    """Configuration for Docker sandbox environment.

    Attributes:
        image: Docker image to use
        network: Network configuration (e.g., 'none', 'host', 'bridge')
        read_only: Whether the container should be read-only
        memory_limit: Memory limit in bytes
        cpu_limit: CPU limit (e.g., '1.0' for one core)
        extra_options: Additional Docker options
    """

    image: str
    network: str = "none"
    read_only: bool = True
    memory_limit: Optional[int] = None
    cpu_limit: Optional[str] = None
    extra_options: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class SecurityPolicy(BaseModel):
    """Security policy configuration.

    Attributes:
        allowed_domains: List of allowed domains for web access
        allowed_commands: List of allowed shell commands
        terminal_sandbox: Docker sandbox configuration for terminal agents
        max_tokens_per_request: Maximum tokens allowed per request
        max_requests_per_minute: Maximum requests allowed per minute
        extra_policies: Additional security policies
    """

    allowed_domains: List[str] = []
    allowed_commands: List[str] = []
    terminal_sandbox: DockerSandboxConfig
    max_tokens_per_request: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    extra_policies: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
