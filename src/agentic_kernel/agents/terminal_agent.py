"""TerminalAgent implementation for executing shell commands.

This module provides an agent specialized in executing shell commands and managing
terminal operations. It supports command execution, output capture, and process
management with proper error handling and security measures.

Key features:
1. Secure command execution with validation
2. Output and error stream capture
3. Process management (background tasks)
4. Environment variable handling
5. Working directory management
6. Command history tracking

Example:
    ```python
    # Initialize the terminal agent
    config = AgentConfig(
        extra_config={
            'plugin_config': {
                'working_dir': '/path/to/workspace',
                'shell': '/bin/bash'
            }
        }
    )
    agent = TerminalAgent(config)
    
    # Execute a command
    task = Task(
        description="List files in current directory",
        parameters={"command": "ls -la"}
    )
    result = await agent.execute(task)
    print(result['output']['stdout'])
    ```
"""

import os
import re
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from enum import Enum, auto

from pydantic import ValidationError

from .base import BaseAgent, TaskCapability
from ..plugins.terminal import TerminalPlugin
from ..config_types import AgentConfig
from ..types import Task, TaskStatus
from ..exceptions import TaskExecutionError

import logging

logger = logging.getLogger(__name__)


class CommandAction(Enum):
    """Supported terminal operations.

    This enum defines the types of operations that the terminal agent
    can perform in the shell environment.
    """

    EXECUTE = auto()  # Execute a command
    BACKGROUND = auto()  # Run a command in background
    KILL = auto()  # Kill a running process


class TerminalResult:
    """Result of a terminal operation.

    This class provides a structured way to return results from terminal
    operations, including command output and any errors.

    Attributes:
        status (TaskStatus): The status of the operation
        output (Optional[Dict[str, Any]]): Operation results if successful
        error (Optional[str]): Error message if operation failed
    """

    def __init__(
        self,
        status: TaskStatus,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.status = status
        self.output = output
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary format.

        Returns:
            Dictionary containing the operation status and results
        """
        return {"status": self.status, "output": self.output, "error": self.error}


class TerminalAgent(BaseAgent):
    """Agent for executing shell commands and managing terminal operations.

    This agent specializes in terminal operations using the TerminalPlugin.
    It can execute commands, manage processes, and handle command output
    with proper security measures and error handling.

    The agent supports working directory management and maintains a secure
    execution environment.

    Attributes:
        plugin (TerminalPlugin): Plugin for terminal operations

    Example:
        ```python
        agent = TerminalAgent(
            config=AgentConfig(
                extra_config={
                    'plugin_config': {
                        'working_dir': '/workspace',
                        'shell': '/bin/bash'
                    }
                }
            )
        )

        # Execute a command
        task = Task(
            description="Check disk usage",
            parameters={"command": "df -h"}
        )
        result = await agent.execute(task)
        if result['status'] == TaskStatus.completed:
            print(result['output']['stdout'])
        ```
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the TerminalAgent.

        Args:
            config: Configuration parameters for the agent, including
                   plugin-specific settings like working_dir and shell

        Example:
            ```python
            config = AgentConfig(
                extra_config={
                    'plugin_config': {
                        'working_dir': Path('/workspace'),
                        'shell': '/bin/bash',
                        'timeout': 30  # seconds
                    }
                }
            )
            agent = TerminalAgent(config)
            ```
        """
        super().__init__(config=config)

        # Configure plugin with provided settings
        plugin_config = self.config.extra_config.get("plugin_config", {})
        if "working_dir" in plugin_config:
            plugin_config["working_dir"] = Path(plugin_config["working_dir"])

        # Initialize terminal plugin
        self.plugin = TerminalPlugin(**plugin_config)
        logger.info(
            f"Initialized TerminalAgent with working dir: "
            f"{plugin_config.get('working_dir', 'default')}"
        )

    def _detect_action(self, description: str) -> CommandAction:
        """Detect the intended terminal operation from the task description.

        This method analyzes the task description to determine which
        terminal operation to perform.

        Args:
            description: Natural language description of the task

        Returns:
            The detected CommandAction

        Example:
            ```python
            action = agent._detect_action("run server in background")
            if action == CommandAction.BACKGROUND:
                # Handle background process
            ```
        """
        description_lower = description.lower()

        if "background" in description_lower:
            return CommandAction.BACKGROUND
        elif "kill" in description_lower or "stop" in description_lower:
            return CommandAction.KILL
        else:
            return CommandAction.EXECUTE

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a terminal operation based on the task description.

        This method parses the task description to determine the desired
        operation and executes it with appropriate parameters.

        Args:
            task: Task containing the operation description and parameters

        Returns:
            Dictionary containing:
            - status: TaskStatus indicating success or failure
            - output: Operation results if successful
            - error: Error message if operation failed

        Raises:
            TaskExecutionError: If task execution fails unexpectedly

        Example:
            ```python
            task = Task(
                description="Run web server in background",
                parameters={
                    "command": "python server.py",
                    "background": True
                }
            )
            result = await agent.execute(task)
            if result['status'] == TaskStatus.completed:
                print(f"Process ID: {result['output']['pid']}")
            ```
        """
        try:
            # Get command from parameters or description
            command = task.parameters.get("command")
            if not command:
                return TerminalResult(
                    status=TaskStatus.failed, error="Command not specified"
                ).to_dict()

            # Detect action type
            action = self._detect_action(task.description)

            # Execute appropriate operation
            if action == CommandAction.BACKGROUND:
                return await self._handle_background(command)
            elif action == CommandAction.KILL:
                return await self._handle_kill(command)
            else:
                return await self._handle_execute(command)

        except Exception as e:
            logger.error(f"Terminal operation failed: {str(e)}", exc_info=True)
            return TerminalResult(
                status=TaskStatus.failed,
                error=f"An unexpected error occurred: {str(e)}",
            ).to_dict()

    async def _handle_execute(self, command: str) -> Dict[str, Any]:
        """Handle command execution.

        Args:
            command: The command to execute

        Returns:
            Operation result with command output

        Example:
            ```python
            result = await agent._handle_execute("ls -la")
            if result['status'] == TaskStatus.completed:
                print(result['output']['stdout'])
            ```
        """
        try:
            result = await self.plugin.execute_command(command)
            return TerminalResult(
                status=TaskStatus.completed,
                output={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.return_code,
                },
            ).to_dict()
        except Exception as e:
            return TerminalResult(
                status=TaskStatus.failed, error=f"Failed to execute command: {str(e)}"
            ).to_dict()

    async def _handle_background(self, command: str) -> Dict[str, Any]:
        """Handle background process execution.

        Args:
            command: The command to run in background

        Returns:
            Operation result with process ID

        Example:
            ```python
            result = await agent._handle_background("python server.py")
            if result['status'] == TaskStatus.completed:
                print(f"Server running with PID: {result['output']['pid']}")
            ```
        """
        try:
            process = await self.plugin.start_background_process(command)
            return TerminalResult(
                status=TaskStatus.completed, output={"pid": process.pid}
            ).to_dict()
        except Exception as e:
            return TerminalResult(
                status=TaskStatus.failed,
                error=f"Failed to start background process: {str(e)}",
            ).to_dict()

    async def _handle_kill(self, pid: Union[str, int]) -> Dict[str, Any]:
        """Handle process termination.

        Args:
            pid: Process ID to terminate

        Returns:
            Operation result indicating success or failure

        Example:
            ```python
            result = await agent._handle_kill("1234")
            if result['status'] == TaskStatus.completed:
                print("Process terminated successfully")
            ```
        """
        try:
            pid = int(pid) if isinstance(pid, str) else pid
            success = await self.plugin.kill_process(pid)
            if success:
                return TerminalResult(
                    status=TaskStatus.completed,
                    output={"message": f"Process {pid} terminated"},
                ).to_dict()
            else:
                return TerminalResult(
                    status=TaskStatus.failed, error=f"Failed to terminate process {pid}"
                ).to_dict()
        except Exception as e:
            return TerminalResult(
                status=TaskStatus.failed, error=f"Failed to kill process: {str(e)}"
            ).to_dict()

    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dictionary mapping task types to their capabilities

        Example:
            ```python
            capabilities = agent._get_supported_tasks()
            for task_type, details in capabilities.items():
                print(f"{task_type}: {details['description']}")
            ```
        """
        return {
            "execute_command": {
                "description": "Execute a shell command",
                "parameters": ["command"],
                "optional_parameters": ["timeout"],
                "examples": [
                    {
                        "description": "List files in directory",
                        "command": "ls -la",
                        "timeout": 30,
                    }
                ],
            },
            "background_command": {
                "description": "Run a command in background",
                "parameters": ["command"],
                "optional_parameters": [],
                "examples": [
                    {"description": "Start web server", "command": "python server.py"}
                ],
            },
            "kill_process": {
                "description": "Terminate a running process",
                "parameters": ["pid"],
                "optional_parameters": [],
                "examples": [{"description": "Kill process with ID 1234", "pid": 1234}],
            },
        }
