"""Tests for the Docker-based sandbox implementation."""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from agentic_kernel.agents.sandbox import DockerSandbox


@pytest.fixture
def docker_sandbox():
    """Create a DockerSandbox instance for testing."""
    return DockerSandbox(
        image="python:3.9-alpine",
        network="none",
        resource_limits={
            "memory": "512m",
            "cpu-shares": 1024,
            "pids-limit": 100
        },
        working_dir="/workspace",
        read_only=True
    )


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_sandbox_initialization(mock_subprocess, docker_sandbox):
    """Test that the sandbox initializes with the correct parameters."""
    assert docker_sandbox.image == "python:3.9-alpine"
    assert docker_sandbox.network == "none"
    assert docker_sandbox.resource_limits["memory"] == "512m"
    assert docker_sandbox.default_working_dir == "/workspace"
    assert docker_sandbox.read_only is True
    assert docker_sandbox.is_running is False


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_ensure_started(mock_subprocess, docker_sandbox):
    """Test the ensure_started method."""
    # Mock the output of docker ps (no container found)
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"")
    process_mock.returncode = 0
    mock_subprocess.return_value = process_mock
    
    # Mock the output of docker run (success)
    next_process_mock = AsyncMock()
    next_process_mock.communicate.return_value = (b"container_id_12345", b"")
    next_process_mock.returncode = 0
    mock_subprocess.side_effect = [process_mock, next_process_mock, process_mock]
    
    result = await docker_sandbox.ensure_started()
    
    assert result is True
    assert docker_sandbox.is_running is True
    assert mock_subprocess.call_count > 0


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_execute_command(mock_subprocess, docker_sandbox):
    """Test the execute_command method."""
    # Set the container as running
    docker_sandbox._running = True
    
    # Mock the output of docker exec
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"test output", b"")
    process_mock.returncode = 0
    mock_subprocess.return_value = process_mock
    
    result = await docker_sandbox.execute_command("ls -l")
    
    assert result["status"] == 0
    assert result["output"] == "test output"
    assert result["error"] == ""
    mock_subprocess.assert_called_once()
    

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_execute_command_error(mock_subprocess, docker_sandbox):
    """Test error handling in execute_command."""
    # Set the container as running
    docker_sandbox._running = True
    
    # Mock the output of docker exec (with error)
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"Permission denied")
    process_mock.returncode = 1
    mock_subprocess.return_value = process_mock
    
    result = await docker_sandbox.execute_command("cat /etc/passwd")
    
    assert result["status"] == 1
    assert result["output"] == ""
    assert result["error"] == "Permission denied"
    

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_execute_command_timeout(mock_subprocess, docker_sandbox):
    """Test timeout handling in execute_command."""
    # Set the container as running
    docker_sandbox._running = True
    
    # Mock a timeout by raising TimeoutError
    process_mock = AsyncMock()
    process_mock.communicate.side_effect = asyncio.TimeoutError("Timeout")
    mock_subprocess.return_value = process_mock
    
    result = await docker_sandbox.execute_command("sleep 100", timeout=1)
    
    assert result["status"] == 1
    assert "timed out" in result["error"]


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_cleanup(mock_subprocess, docker_sandbox):
    """Test the cleanup method."""
    # Set the container as running
    docker_sandbox._running = True
    docker_sandbox._container_id = "container_id_12345"
    
    # Mock the docker stop command
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"")
    mock_subprocess.return_value = process_mock
    
    await docker_sandbox.cleanup()
    
    assert docker_sandbox.is_running is False
    assert docker_sandbox._container_id is None
    assert mock_subprocess.call_count > 0


@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_reset(mock_subprocess, docker_sandbox):
    """Test the reset method."""
    # Set the container as running
    docker_sandbox._running = True
    docker_sandbox._container_id = "container_id_12345"
    
    # Mock the docker stop and docker run commands
    process_mock = AsyncMock()
    process_mock.communicate.return_value = (b"", b"")
    process_mock.returncode = 0
    
    start_process_mock = AsyncMock()
    start_process_mock.communicate.return_value = (b"new_container_id", b"")
    start_process_mock.returncode = 0
    
    # Return different process mocks for different calls
    mock_subprocess.side_effect = [process_mock, process_mock, start_process_mock, process_mock]
    
    result = await docker_sandbox.reset()
    
    assert result is True
    assert docker_sandbox.is_running is True 