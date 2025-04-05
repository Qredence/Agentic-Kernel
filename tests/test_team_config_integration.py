"""Tests for integration of agent team configuration with ConfigLoader."""

import pytest
import os
import json
import tempfile
from typing import Dict, Any

from agentic_kernel.config import (
    AgentTeamConfig,
    AgentConfig,
    SecurityPolicy,
    DockerSandboxConfig
)
from agentic_kernel.config.loader import ConfigLoader, KernelConfig


@pytest.fixture
def sample_team_config() -> Dict[str, Any]:
    """Sample team configuration for testing."""
    return {
        "team_name": "test_team",
        "description": "Test agent team",
        "agents": [
            {
                "name": "orchestrator",
                "type": "OrchestratorAgent",
                "description": "Test orchestrator agent",
                "llm_mapping": {
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                "config": {}
            },
            {
                "name": "terminal",
                "type": "TerminalAgent",
                "description": "Test terminal agent",
                "llm_mapping": {
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.2,
                    "max_tokens": 1000
                },
                "config": {
                    "sandbox_type": "docker",
                    "allowed_commands": ["ls", "cat"],
                    "sandbox_options": {
                        "image": "python:3.9-alpine",
                        "read_only": True
                    }
                }
            }
        ],
        "security_policy": {
            "allowed_domains": ["github.com"],
            "allowed_commands": ["ls", "cat"],
            "terminal_sandbox": {
                "image": "python:3.9-alpine",
                "network": "none"
            }
        }
    }


@pytest.fixture
def sample_config_json(sample_team_config) -> str:
    """Generate a temporary config file for testing."""
    config_data = {
        "version": "0.2.0",
        "endpoints": {
            "openai": {
                "type": "openai",
                "endpoint_url": "https://api.openai.com/v1",
                "api_key": "test_key",
                "default_model": "gpt-4-turbo-preview",
                "models": {
                    "gpt-4-turbo-preview": {
                        "model_name": "gpt-4-turbo-preview",
                        "max_tokens": 4096,
                        "temperature": 0.7
                    }
                }
            }
        },
        "default_endpoint": "openai",
        "default_model": "gpt-4-turbo-preview",
        "agent_teams": {
            "test_team": sample_team_config
        },
        "default_team": "test_team"
    }
    
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump(config_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    os.unlink(temp_path)


def test_config_loader_with_team(sample_config_json):
    """Test that ConfigLoader correctly loads team configurations."""
    config_loader = ConfigLoader.from_file(sample_config_json)
    
    # Check that the team config was loaded
    assert "test_team" in config_loader.config.agent_teams
    
    # Check team retrieval methods
    team_config = config_loader.get_agent_team_config()
    assert team_config.team_name == "test_team"
    assert len(team_config.agents) == 2
    
    # Check agent retrieval
    agent_config = config_loader.get_agent_config("terminal")
    assert agent_config.name == "terminal"
    assert agent_config.type == "TerminalAgent"
    assert "sandbox_type" in agent_config.config
    assert agent_config.config["sandbox_type"] == "docker"
    
    # Check security policy retrieval
    security_policy = config_loader.get_security_policy()
    assert "github.com" in security_policy.allowed_domains
    assert security_policy.terminal_sandbox.image == "python:3.9-alpine"


def test_programmatic_team_config():
    """Test creating and using team configurations programmatically."""
    # Create a team config
    team_config = AgentTeamConfig(
        team_name="test_team",
        description="Test team",
        agents=[
            AgentConfig(
                name="terminal",
                type="TerminalAgent",
                description="Terminal agent",
                config={
                    "sandbox_type": "docker",
                    "allowed_commands": ["ls", "cat"]
                }
            )
        ],
        security_policy=SecurityPolicy(
            allowed_commands=["ls", "cat"],
            terminal_sandbox=DockerSandboxConfig(
                image="alpine:latest",
                network="none"
            )
        )
    )
    
    # Create kernel config with the team
    kernel_config = KernelConfig()
    kernel_config.agent_teams["test_team"] = team_config
    kernel_config.default_team = "test_team"
    
    # Create config loader with the kernel config
    config_loader = ConfigLoader(kernel_config)
    
    # Check that the team was added
    assert "test_team" in config_loader.config.agent_teams
    
    # Check that we can retrieve the agent
    agent_config = config_loader.get_agent_config("terminal")
    assert agent_config.name == "terminal"
    assert agent_config.type == "TerminalAgent"
    
    # Add a team using the add_agent_team method
    new_team = AgentTeamConfig(
        team_name="another_team",
        description="Another test team",
        agents=[
            AgentConfig(
                name="web_surfer",
                type="WebSurferAgent",
                description="Web agent"
            )
        ]
    )
    
    config_loader.add_agent_team(new_team)
    
    # Check that the new team was added
    assert "another_team" in config_loader.config.agent_teams
    
    # Check that we can retrieve the team
    another_team = config_loader.get_agent_team_config("another_team")
    assert another_team.team_name == "another_team"
    assert len(another_team.agents) == 1
    assert another_team.agents[0].name == "web_surfer" 