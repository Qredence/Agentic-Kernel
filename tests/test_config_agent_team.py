"""Tests for agent team configuration schema."""

import pytest
from typing import Dict, Any
from pydantic import ValidationError

from agentic_kernel.config.agent_team import (
    AgentTeamConfig,
    AgentConfig,
    LLMMapping,
    SecurityPolicy
)

@pytest.fixture
def valid_agent_config() -> Dict[str, Any]:
    """Valid configuration for a single agent."""
    return {
        "name": "web_surfer",
        "type": "WebSurferAgent",
        "description": "Agent for web research",
        "llm_mapping": {
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "config": {
            "max_search_results": 5,
            "timeout": 30
        }
    }

@pytest.fixture
def valid_team_config() -> Dict[str, Any]:
    """Valid configuration for an agent team."""
    return {
        "team_name": "research_team",
        "description": "Team for research tasks",
        "agents": [
            {
                "name": "web_surfer",
                "type": "WebSurferAgent",
                "description": "Agent for web research",
                "llm_mapping": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "config": {
                    "max_search_results": 5,
                    "timeout": 30
                }
            },
            {
                "name": "file_surfer",
                "type": "FileSurferAgent",
                "description": "Agent for file operations",
                "llm_mapping": {
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.5,
                    "max_tokens": 800
                },
                "config": {
                    "max_file_size": 10000000,
                    "allowed_extensions": [".txt", ".md", ".py"]
                }
            }
        ],
        "security_policy": {
            "allowed_domains": ["github.com", "docs.python.org"],
            "blocked_domains": ["example.com"],
            "max_parallel_tasks": 3,
            "max_tokens_per_request": 4000,
            "allowed_file_extensions": [".txt", ".md", ".py", ".json"],
            "blocked_file_extensions": [".exe", ".sh"],
            "allowed_commands": ["git", "pip"],
            "blocked_commands": ["rm", "sudo"]
        }
    }

def test_valid_agent_config(valid_agent_config):
    """Test that a valid agent configuration is accepted."""
    agent_config = AgentConfig(**valid_agent_config)
    assert agent_config.name == "web_surfer"
    assert agent_config.type == "WebSurferAgent"
    assert agent_config.llm_mapping.model == "gpt-4"
    assert agent_config.config["max_search_results"] == 5

def test_invalid_agent_config():
    """Test that invalid agent configurations are rejected."""
    # Missing required fields
    with pytest.raises(ValidationError):
        AgentConfig(
            name="test",
            type="UnknownAgent"
        )
    
    # Invalid LLM mapping
    with pytest.raises(ValidationError):
        AgentConfig(
            name="test",
            type="WebSurferAgent",
            description="Test agent",
            llm_mapping={
                "model": "",  # Empty model name
                "temperature": 2.0  # Temperature out of range
            }
        )

def test_valid_team_config(valid_team_config):
    """Test that a valid team configuration is accepted."""
    team_config = AgentTeamConfig(**valid_team_config)
    assert team_config.team_name == "research_team"
    assert len(team_config.agents) == 2
    assert team_config.security_policy.max_parallel_tasks == 3

def test_invalid_team_config(valid_team_config):
    """Test that invalid team configurations are rejected."""
    # Empty team
    invalid_config = valid_team_config.copy()
    invalid_config["agents"] = []
    with pytest.raises(ValidationError):
        AgentTeamConfig(**invalid_config)
    
    # Duplicate agent names
    invalid_config = valid_team_config.copy()
    invalid_config["agents"].append(invalid_config["agents"][0].copy())
    with pytest.raises(ValidationError):
        AgentTeamConfig(**invalid_config)

def test_security_policy_validation(valid_team_config):
    """Test security policy validation rules."""
    policy = SecurityPolicy(**valid_team_config["security_policy"])
    
    # Test domain validation
    assert "github.com" in policy.allowed_domains
    assert "example.com" in policy.blocked_domains
    
    # Test file extension validation
    assert ".py" in policy.allowed_file_extensions
    assert ".exe" in policy.blocked_file_extensions
    
    # Test command validation
    assert "git" in policy.allowed_commands
    assert "sudo" in policy.blocked_commands

def test_llm_mapping_validation():
    """Test LLM mapping validation rules."""
    # Valid mapping
    valid_mapping = LLMMapping(
        model="gpt-4",
        temperature=0.7,
        max_tokens=1000
    )
    assert valid_mapping.model == "gpt-4"
    
    # Invalid temperature
    with pytest.raises(ValidationError):
        LLMMapping(
            model="gpt-4",
            temperature=1.5,  # Must be between 0 and 1
            max_tokens=1000
        )
    
    # Invalid max_tokens
    with pytest.raises(ValidationError):
        LLMMapping(
            model="gpt-4",
            temperature=0.7,
            max_tokens=-1  # Must be positive
        )

def test_agent_config_defaults():
    """Test default values in agent configuration."""
    minimal_config = {
        "name": "test_agent",
        "type": "WebSurferAgent",
        "description": "Test agent"
    }
    agent_config = AgentConfig(**minimal_config)
    
    # Check default LLM mapping
    assert agent_config.llm_mapping.temperature == 0.7  # Default temperature
    assert agent_config.llm_mapping.max_tokens == 1000  # Default max tokens
    
    # Check empty config dict
    assert isinstance(agent_config.config, dict)
    assert len(agent_config.config) == 0

def test_security_policy_defaults():
    """Test default values in security policy."""
    policy = SecurityPolicy()
    
    # Check default lists are empty but initialized
    assert isinstance(policy.allowed_domains, list)
    assert isinstance(policy.blocked_domains, list)
    assert isinstance(policy.allowed_commands, list)
    assert isinstance(policy.blocked_commands, list)
    
    # Check default numeric values
    assert policy.max_parallel_tasks == 5  # Default value
    assert policy.max_tokens_per_request == 4000  # Default value 