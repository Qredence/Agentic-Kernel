"""Tests for the TerminalAgent implementation."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from agentic_kernel.agents.terminal_agent import TerminalAgent


@pytest.fixture
def mock_sandbox():
    sandbox = Mock()
    sandbox.execute_command = Mock()
    sandbox.get_output = Mock()
    return sandbox


@pytest.fixture
def terminal_agent(mock_sandbox):
    return TerminalAgent(
        name="test_terminal",
        description="Test terminal agent",
        sandbox=mock_sandbox,
        config={
            "allowed_commands": ["ls", "cat", "grep", "find"],
            "max_output_size": 1024 * 1024,  # 1MB
            "timeout": 30,  # seconds
            "working_directory": "/workspace"
        }
    )


async def test_terminal_initialization(terminal_agent):
    """Test that the terminal agent is initialized correctly."""
    assert terminal_agent.name == "test_terminal"
    assert terminal_agent.description == "Test terminal agent"
    assert "ls" in terminal_agent.config["allowed_commands"]
    assert terminal_agent.config["max_output_size"] == 1024 * 1024
    assert terminal_agent.config["timeout"] == 30
    assert terminal_agent.config["working_directory"] == "/workspace"


async def test_command_execution(terminal_agent, mock_sandbox):
    """Test command execution functionality."""
    mock_sandbox.execute_command.return_value = {
        "status": 0,
        "output": "file1.txt\nfile2.txt",
        "error": ""
    }
    
    result = await terminal_agent.execute_command("ls -l")
    
    assert result["status"] == 0
    assert "file1.txt" in result["output"]
    assert not result["error"]
    mock_sandbox.execute_command.assert_called_once_with(
        "ls -l",
        timeout=30,
        working_dir="/workspace"
    )


async def test_command_validation(terminal_agent):
    """Test command validation."""
    # Test allowed command
    assert terminal_agent.is_command_allowed("ls -l") is True
    assert terminal_agent.is_command_allowed("cat file.txt") is True
    
    # Test disallowed command
    assert terminal_agent.is_command_allowed("rm -rf /") is False
    assert terminal_agent.is_command_allowed("sudo apt-get install") is False


async def test_output_size_limit(terminal_agent, mock_sandbox):
    """Test output size limiting."""
    large_output = "x" * (1024 * 1024 + 1)  # Exceeds max_output_size
    mock_sandbox.execute_command.return_value = {
        "status": 0,
        "output": large_output,
        "error": ""
    }
    
    with pytest.raises(ValueError, match="Output size exceeds limit"):
        await terminal_agent.execute_command("cat large_file.txt")


async def test_command_timeout(terminal_agent, mock_sandbox):
    """Test command timeout handling."""
    mock_sandbox.execute_command.side_effect = TimeoutError("Command timed out")
    
    result = await terminal_agent.execute_command("sleep 100")
    
    assert result["status"] == 1
    assert "timed out" in result["error"].lower()


async def test_working_directory(terminal_agent, mock_sandbox):
    """Test working directory handling."""
    mock_sandbox.execute_command.return_value = {
        "status": 0,
        "output": "/workspace/project",
        "error": ""
    }
    
    result = await terminal_agent.execute_command("pwd")
    
    assert result["status"] == 0
    assert "/workspace" in result["output"]
    mock_sandbox.execute_command.assert_called_with(
        "pwd",
        timeout=30,
        working_dir="/workspace"
    )


async def test_error_handling(terminal_agent, mock_sandbox):
    """Test error handling in command execution."""
    # Test command not found
    mock_sandbox.execute_command.return_value = {
        "status": 127,
        "output": "",
        "error": "command not found"
    }
    
    result = await terminal_agent.execute_command("nonexistent_command")
    
    assert result["status"] == 127
    assert "command not found" in result["error"].lower()
    
    # Test permission denied
    mock_sandbox.execute_command.return_value = {
        "status": 1,
        "output": "",
        "error": "Permission denied"
    }
    
    result = await terminal_agent.execute_command("cat /root/secret.txt")
    
    assert result["status"] == 1
    assert "permission denied" in result["error"].lower()


async def test_execute_task(terminal_agent, mock_sandbox):
    """Test the execute_task method."""
    task_description = "List all Python files in the current directory"
    context = {
        "command": "find . -name '*.py'",
        "working_directory": "/workspace/project"
    }
    
    mock_sandbox.execute_command.return_value = {
        "status": 0,
        "output": "./src/main.py\n./tests/test_main.py",
        "error": ""
    }
    
    result = await terminal_agent.execute_task(task_description, context)
    
    assert result["status"] == "success"
    assert "main.py" in result["output"]["output"]
    mock_sandbox.execute_command.assert_called_once()


async def test_sandbox_cleanup(terminal_agent, mock_sandbox):
    """Test sandbox cleanup after task execution."""
    mock_sandbox.cleanup = Mock()
    
    await terminal_agent.cleanup()
    
    mock_sandbox.cleanup.assert_called_once()


async def test_command_history(terminal_agent, mock_sandbox):
    """Test command history tracking."""
    commands = [
        "ls -l",
        "cat file.txt",
        "grep pattern file.txt"
    ]
    
    mock_sandbox.execute_command.return_value = {
        "status": 0,
        "output": "",
        "error": ""
    }
    
    for cmd in commands:
        await terminal_agent.execute_command(cmd)
    
    history = terminal_agent.get_command_history()
    
    assert len(history) == 3
    assert history == commands 