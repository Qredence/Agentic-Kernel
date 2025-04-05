"""Tests for base agent implementation."""

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock
from agentic_kernel.config import AgentConfig
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.types import Task


def test_agent_config_validation():
    """Test agent configuration validation."""
    # Test valid config
    valid_config = AgentConfig(name="test_agent", model="gpt-4")
    assert valid_config.name == "test_agent"
    assert valid_config.model == "gpt-4"
    
    # Test invalid config (missing required fields)
    with pytest.raises(ValidationError):
        AgentConfig()


def test_base_agent_initialization():
    """Test base agent initialization."""
    config = AgentConfig(name="test_agent", model="gpt-4")
    agent = BaseAgent(config=config)
    assert agent.config == config
    assert agent.name == "test_agent"


@pytest.mark.asyncio
async def test_base_agent_handle_message():
    """Test base agent handle_message raises NotImplementedError."""
    config = AgentConfig(name="test_agent", model="gpt-4")
    agent = BaseAgent(config=config)
    
    # Base agent's handle_message should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        agent.handle_message("test message")
