"""Tests for base agent classes."""

import pytest
from unittest.mock import AsyncMock, patch
from ..utils.base_agent import Agent, FunctionTool, InMemorySessionService

def test_agent_initialization():
    """Test Agent initialization."""
    agent = Agent(
        name="test_agent",
        model="test_model",
        instruction="test instruction"
    )
    
    assert agent.name == "test_agent"
    assert agent.model == "test_model"
    assert agent.instruction == "test instruction"
    assert agent.tools == []

def test_agent_add_tool():
    """Test adding tools to an agent."""
    agent = Agent(
        name="test_agent",
        model="test_model",
        instruction="test instruction"
    )
    
    def test_function():
        return "test"
    
    tool = FunctionTool(
        name="test_tool",
        description="test description",
        function=test_function
    )
    
    agent.add_tool(tool)
    assert len(agent.tools) == 1
    assert agent.tools[0].name == "test_tool"
    assert agent.tools[0].description == "test description"
    assert agent.tools[0].function() == "test"

def test_session_service():
    """Test session service functionality."""
    service = InMemorySessionService()
    session = service.create_session(
        state={"test": "state"},
        app_name="test_app",
        user_id="test_user"
    )
    
    assert session["state"] == {"test": "state"}
    assert session["app_name"] == "test_app"
    assert session["user_id"] == "test_user" 