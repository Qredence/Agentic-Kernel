"""Configuration loader for AgenticFleet."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from . import LLM_CONFIG_PATH


class LLMEndpointConfig(BaseModel):
    """Configuration for an LLM endpoint."""
    type: str
    models: Dict[str, Dict[str, Any]]


class LLMConfig(BaseModel):
    """Configuration for LLM services."""
    version: str
    endpoints: Dict[str, LLMEndpointConfig]
    default_config: Dict[str, Any]


class ConfigLoader:
    """Configuration loader for AgenticFleet."""
    
    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize the configuration loader.
        
        Args:
            config_path: Optional path to the configuration file
        """
        self.config_path = config_path or LLM_CONFIG_PATH
        self._config: Optional[LLMConfig] = None
    
    @property
    def llm_config(self) -> LLMConfig:
        """Get the LLM configuration.
        
        Returns:
            LLMConfig object
        """
        if self._config is None:
            with open(self.config_path) as f:
                config_data = json.load(f)
            self._config = LLMConfig(**config_data)
        return self._config
    
    def get_model_config(self, endpoint: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific model.
        
        Args:
            endpoint: Optional endpoint name (defaults to default_config.endpoint)
            model: Optional model name (defaults to default_config.model)
            
        Returns:
            Dictionary containing model configuration
            
        Raises:
            ValueError: If endpoint or model is not found
        """
        config = self.llm_config
        
        # Use defaults if not specified
        endpoint = endpoint or config.default_config["endpoint"]
        model = model or config.default_config["model"]
        
        # Validate endpoint exists
        if endpoint not in config.endpoints:
            raise ValueError(f"Endpoint '{endpoint}' not found in configuration")
            
        endpoint_config = config.endpoints[endpoint]
        
        # Validate model exists
        if model not in endpoint_config.models:
            raise ValueError(f"Model '{model}' not found in endpoint '{endpoint}'")
            
        # Combine model config with defaults
        model_config = endpoint_config.models[model].copy()
        model_config.update({
            "endpoint": endpoint,
            "endpoint_type": endpoint_config.type
        })
        
        # Add default settings if not specified in model config
        for key, value in config.default_config.items():
            if key not in model_config and key not in ["endpoint", "model"]:
                model_config[key] = value
                
        return model_config 