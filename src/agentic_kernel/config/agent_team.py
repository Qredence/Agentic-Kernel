"""Configuration schema for agent teams."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator, constr

class LLMMapping(BaseModel):
    """Configuration for LLM settings per agent."""
    
    model: constr(min_length=1) = Field(
        default="gpt-4o-mini",
        description="The LLM model to use (e.g., gpt-4, gpt-3.5-turbo)"
    )
    endpoint: constr(min_length=1) = Field(
        default="azure_openai",
        description="The endpoint to use (e.g., azure_openai)"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Sampling temperature for the LLM"
    )
    max_tokens: int = Field(
        default=1000,
        gt=0,
        description="Maximum tokens per request"
    )
    
    class Config:
        frozen = True

class DockerSandboxConfig(BaseModel):
    """Configuration for Docker-based sandbox."""
    
    image: str = Field(
        default="alpine:latest",
        description="Docker image to use for the sandbox"
    )
    network: str = Field(
        default="none",
        description="Network configuration (none, host, bridge, etc.)"
    )
    memory_limit: str = Field(
        default="512m",
        description="Memory limit for the container"
    )
    cpu_limit: int = Field(
        default=1,
        gt=0,
        description="CPU limit for the container (1 = 1 CPU core)"
    )
    read_only: bool = Field(
        default=True,
        description="Whether the container filesystem should be read-only"
    )
    volumes: List[str] = Field(
        default_factory=list,
        description="Volume mount specifications"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
    working_directory: str = Field(
        default="/workspace",
        description="Default working directory in the container"
    )
    
    class Config:
        frozen = True

class SecurityPolicy(BaseModel):
    """Security policy for agent team operations."""
    
    allowed_domains: List[str] = Field(
        default_factory=list,
        description="List of allowed domains for web access"
    )
    blocked_domains: List[str] = Field(
        default_factory=list,
        description="List of blocked domains"
    )
    allowed_file_extensions: List[str] = Field(
        default_factory=list,
        description="List of allowed file extensions"
    )
    blocked_file_extensions: List[str] = Field(
        default_factory=list,
        description="List of blocked file extensions"
    )
    allowed_commands: List[str] = Field(
        default_factory=lambda: ["ls", "cat", "grep", "find"],
        description="List of allowed shell commands"
    )
    blocked_commands: List[str] = Field(
        default_factory=list,
        description="List of blocked shell commands"
    )
    max_parallel_tasks: int = Field(
        default=5,
        gt=0,
        description="Maximum number of parallel tasks"
    )
    max_tokens_per_request: int = Field(
        default=4000,
        gt=0,
        description="Maximum tokens per LLM request"
    )
    terminal_sandbox: DockerSandboxConfig = Field(
        default_factory=DockerSandboxConfig,
        description="Configuration for the terminal agent sandbox"
    )
    
    @validator("allowed_domains", "blocked_domains")
    def validate_domains(cls, v: List[str]) -> List[str]:
        """Validate domain names."""
        for domain in v:
            if not domain or " " in domain:
                raise ValueError(f"Invalid domain name: {domain}")
        return v
    
    @validator("allowed_file_extensions", "blocked_file_extensions")
    def validate_extensions(cls, v: List[str]) -> List[str]:
        """Validate file extensions."""
        for ext in v:
            if not ext.startswith(".") or " " in ext:
                raise ValueError(f"Invalid file extension: {ext}")
        return v
    
    @validator("allowed_commands", "blocked_commands")
    def validate_commands(cls, v: List[str]) -> List[str]:
        """Validate command names."""
        for cmd in v:
            if not cmd or " " in cmd:
                raise ValueError(f"Invalid command name: {cmd}")
        return v
    
    class Config:
        frozen = True

class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    
    name: constr(min_length=1) = Field(
        ...,
        description="Unique name for the agent"
    )
    type: constr(min_length=1) = Field(
        ...,
        description="Type of agent (e.g., WebSurferAgent)"
    )
    description: str = Field(
        ...,
        description="Description of the agent's purpose"
    )
    llm_mapping: LLMMapping = Field(
        default_factory=lambda: LLMMapping(),
        description="LLM configuration for this agent"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Agent-specific configuration"
    )
    
    class Config:
        frozen = True

class AgentTeamConfig(BaseModel):
    """Configuration for a team of agents."""
    
    team_name: constr(min_length=1) = Field(
        ...,
        description="Name of the agent team"
    )
    description: str = Field(
        ...,
        description="Description of the team's purpose"
    )
    agents: List[AgentConfig] = Field(
        ...,
        min_items=1,
        description="List of agents in the team"
    )
    security_policy: SecurityPolicy = Field(
        default_factory=SecurityPolicy,
        description="Security policy for the team"
    )
    
    @validator("agents")
    def validate_unique_agent_names(cls, v: List[AgentConfig]) -> List[AgentConfig]:
        """Ensure agent names are unique within the team."""
        names = [agent.name for agent in v]
        if len(names) != len(set(names)):
            raise ValueError("Agent names must be unique within a team")
        return v
    
    class Config:
        frozen = True 