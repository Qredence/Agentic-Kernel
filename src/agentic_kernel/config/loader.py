"""Configuration management for agentic-kernel."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union, List

from pydantic import BaseModel, Field

from .agent_team import AgentTeamConfig, AgentConfig, SecurityPolicy


class ModelConfig(BaseModel):
    """Configuration for a specific model."""
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.95
    presence_penalty: float = 0
    frequency_penalty: float = 0
    store: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    multimodal: bool = False
    optimized_for: Optional[str] = None


class EndpointConfig(BaseModel):
    """Configuration for an LLM endpoint."""
    type: str
    endpoint_url: str
    models: Dict[str, ModelConfig]
    api_version: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None


class KernelConfig(BaseModel):
    """Configuration for the agentic kernel."""
    version: str = "0.2.0"
    endpoints: Dict[str, EndpointConfig] = Field(default_factory=dict)
    default_endpoint: Optional[str] = None
    default_model: Optional[str] = None
    request_timeout: int = 300
    retry_on_failure: bool = True
    max_retries: int = 3
    cache_seed: Optional[int] = None
    agent_teams: Dict[str, AgentTeamConfig] = Field(default_factory=dict)
    default_team: Optional[str] = None


class ConfigLoader:
    """Configuration loader for agentic-kernel.
    
    This class manages configuration for the agentic-kernel library. It can load
    configuration from a file or accept it programmatically through the constructor.
    
    Example:
        ```python
        # Load from file
        config = ConfigLoader.from_file("config.json")
        
        # Create programmatically
        config = ConfigLoader(KernelConfig(
            endpoints={
                "my_endpoint": EndpointConfig(
                    type="azure_openai",
                    endpoint_url="https://my-endpoint.com",
                    models={
                        "gpt-4": ModelConfig(
                            model_name="gpt-4",
                            max_tokens=4096
                        )
                    }
                )
            },
            default_endpoint="my_endpoint"
        ))
        ```
    """
    
    def __init__(
        self,
        config: Optional[Union[KernelConfig, Dict[str, Any]]] = None,
        *,
        validate: bool = True
    ) -> None:
        """Initialize the configuration loader.
        
        Args:
            config: Configuration data, either as a KernelConfig object or a dictionary.
                If None, creates a default configuration.
            validate: Whether to validate the configuration. Defaults to True.
        """
        if config is None:
            self._config = KernelConfig()
        elif isinstance(config, dict):
            self._config = KernelConfig(**config)
        elif isinstance(config, KernelConfig):
            self._config = config
        else:
            raise TypeError(f"Expected dict or KernelConfig, got {type(config)}")
        
        if validate:
            self._validate_config()
    
    @classmethod
    def from_file(cls, path: Union[str, Path], *, validate: bool = True) -> "ConfigLoader":
        """Create a ConfigLoader instance from a JSON file.
        
        Args:
            path: Path to the configuration file
            validate: Whether to validate the configuration
            
        Returns:
            ConfigLoader instance
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path) as f:
            config_data = json.load(f)
        
        return cls(config_data, validate=validate)
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        if not self._config.endpoints and self._config.default_endpoint:
            raise ValueError("Default endpoint specified but no endpoints defined")
        
        if self._config.default_endpoint and self._config.default_endpoint not in self._config.endpoints:
            raise ValueError(f"Default endpoint '{self._config.default_endpoint}' not found in endpoints")
        
        for name, endpoint in self._config.endpoints.items():
            if not endpoint.models:
                raise ValueError(f"No models defined for endpoint '{name}'")
            
            if endpoint.default_model and endpoint.default_model not in endpoint.models:
                raise ValueError(f"Default model '{endpoint.default_model}' not found in endpoint '{name}'")
        
        if self._config.default_team and self._config.default_team not in self._config.agent_teams:
            raise ValueError(f"Default team '{self._config.default_team}' not found in agent_teams")
    
    @property
    def config(self) -> KernelConfig:
        """Get the kernel configuration.
        
        Returns:
            KernelConfig object
        """
        return self._config
    
    def get_model_config(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get configuration for a specific model.
        
        Args:
            endpoint: Optional endpoint name (defaults to default_endpoint)
            model: Optional model name (defaults to endpoint's default_model or config's default_model)
            
        Returns:
            Dictionary containing model configuration
            
        Raises:
            ValueError: If endpoint or model is not found
        """
        # Determine endpoint
        endpoint_name = endpoint or self._config.default_endpoint
        if not endpoint_name:
            raise ValueError("No endpoint specified and no default endpoint configured")
        
        if endpoint_name not in self._config.endpoints:
            raise ValueError(f"Endpoint '{endpoint_name}' not found")
        
        endpoint_config = self._config.endpoints[endpoint_name]
        
        # Determine model
        model_name = model or endpoint_config.default_model or self._config.default_model
        if not model_name:
            raise ValueError("No model specified and no default model configured")
        
        if model_name not in endpoint_config.models:
            raise ValueError(f"Model '{model_name}' not found in endpoint '{endpoint_name}'")
        
        model_config = endpoint_config.models[model_name]
        
        # Build configuration dictionary
        config = model_config.model_dump()
        config.update({
            "endpoint": endpoint_name,
            "endpoint_type": endpoint_config.type,
            "endpoint_url": endpoint_config.endpoint_url,
            "api_version": endpoint_config.api_version,
            "api_key": endpoint_config.api_key
        })
        
        return config
    
    def get_agent_team_config(self, team_name: Optional[str] = None) -> AgentTeamConfig:
        """Get configuration for a specific agent team.
        
        Args:
            team_name: Optional team name (defaults to default_team)
            
        Returns:
            AgentTeamConfig object
            
        Raises:
            ValueError: If team is not found
        """
        # Determine team
        team_name = team_name or self._config.default_team
        if not team_name:
            raise ValueError("No team specified and no default team configured")
        
        if team_name not in self._config.agent_teams:
            raise ValueError(f"Agent team '{team_name}' not found")
        
        return self._config.agent_teams[team_name]
    
    def get_agent_config(self, agent_name: str, team_name: Optional[str] = None) -> AgentConfig:
        """Get configuration for a specific agent within a team.
        
        Args:
            agent_name: Name of the agent
            team_name: Optional team name (defaults to default_team)
            
        Returns:
            AgentConfig object
            
        Raises:
            ValueError: If team or agent is not found
        """
        team_config = self.get_agent_team_config(team_name)
        
        for agent in team_config.agents:
            if agent.name == agent_name:
                return agent
        
        raise ValueError(f"Agent '{agent_name}' not found in team '{team_name}'")
    
    def get_security_policy(self, team_name: Optional[str] = None) -> SecurityPolicy:
        """Get security policy for a specific team.
        
        Args:
            team_name: Optional team name (defaults to default_team)
            
        Returns:
            SecurityPolicy object
            
        Raises:
            ValueError: If team is not found
        """
        team_config = self.get_agent_team_config(team_name)
        return team_config.security_policy
    
    def add_agent_team(self, team_config: AgentTeamConfig) -> None:
        """Add or update an agent team configuration.
        
        Args:
            team_config: AgentTeamConfig to add
        """
        self._config.agent_teams[team_config.team_name] = team_config 