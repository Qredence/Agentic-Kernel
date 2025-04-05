"""TerminalAgent implementation for secure command execution in a sandbox environment."""

import os
import re
from typing import Dict, Any, Optional, List, Union
from .base import BaseAgent
from .sandbox import Sandbox, DockerSandbox


class TerminalAgent(Agent):
    """Agent responsible for executing terminal commands in a secure sandbox."""

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        sandbox: Optional[Sandbox] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the TerminalAgent.
        
        Args:
            name: The unique name of the agent
            description: A brief description of the agent's capabilities
            sandbox: The sandbox environment for command execution
            config: Configuration options including allowed_commands, max_output_size,
                   timeout, working_directory, and sandbox_options
        """
        super().__init__(name, description, config)
        self.config = config or {}
        
        # Set up sandbox
        if sandbox:
            self.sandbox = sandbox
        else:
            # Create sandbox based on configuration
            sandbox_type = self.config.get("sandbox_type", "docker")
            sandbox_options = self.config.get("sandbox_options", {})
            
            if sandbox_type == "docker":
                self.sandbox = DockerSandbox(**sandbox_options)
            else:
                raise ValueError(f"Unsupported sandbox type: {sandbox_type}")
        
        # Set up security parameters
        self.allowed_commands = self.config.get("allowed_commands", ["ls", "cat", "grep", "find"])
        self.max_output_size = self.config.get("max_output_size", 1024 * 1024)  # 1MB default
        self.timeout = self.config.get("timeout", 30)  # 30 seconds default
        self.working_directory = self.config.get("working_directory", "/workspace")
        self.command_history: List[str] = []

    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a terminal task based on the task description and context.
        
        Args:
            task_description: Description of the terminal task to perform
            context: Additional context including command and working directory
            
        Returns:
            Dict containing the execution results and status
        """
        if not context:
            context = {}
            
        command = context.get("command")
        if not command:
            return {
                "status": "error",
                "error": "No command provided in context"
            }
            
        working_dir = context.get("working_directory", self.working_directory)
        
        try:
            if not self.is_command_allowed(command):
                return {
                    "status": "error",
                    "error": f"Command '{command}' is not allowed"
                }
                
            result = await self.execute_command(command, working_dir)
            
            return {
                "status": "success" if result["status"] == 0 else "error",
                "output": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def execute_command(
        self,
        command: str,
        working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command in the sandbox environment.
        
        Args:
            command: The command to execute
            working_dir: Optional working directory for command execution
            
        Returns:
            Dict containing command execution results
        """
        if not self.is_command_allowed(command):
            raise ValueError(f"Command '{command}' is not allowed")
            
        working_dir = working_dir or self.working_directory
        
        try:
            result = await self.sandbox.execute_command(
                command,
                timeout=self.timeout,
                working_dir=working_dir
            )
            
            # Check output size
            output_size = len(result["output"]) + len(result["error"])
            if output_size > self.max_output_size:
                raise ValueError("Output size exceeds limit")
                
            # Record command in history
            self.command_history.append(command)
            
            return result
        except TimeoutError:
            return {
                "status": 1,
                "output": "",
                "error": f"Command timed out after {self.timeout} seconds"
            }
        except Exception as e:
            return {
                "status": 1,
                "output": "",
                "error": str(e)
            }

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed to be executed.
        
        Args:
            command: The command to check
            
        Returns:
            True if the command is allowed, False otherwise
        """
        # Extract the base command (first word)
        base_command = command.split()[0]
        
        # Check if base command is in allowed list
        if base_command not in self.allowed_commands:
            return False
            
        # Check for dangerous patterns
        dangerous_patterns = [
            r"[|;&`$]",  # Shell metacharacters
            r"sudo\s",    # Sudo commands
            r">\s*/",     # Writing to root
            r"rm\s+-rf",  # Recursive force remove
        ]
        
        return not any(re.search(pattern, command) for pattern in dangerous_patterns)

    def get_command_history(self) -> List[str]:
        """Get the history of executed commands.
        
        Returns:
            List of previously executed commands
        """
        return self.command_history.copy()

    async def cleanup(self) -> None:
        """Clean up the sandbox environment."""
        if hasattr(self.sandbox, 'cleanup'):
            await self.sandbox.cleanup()

    def add_allowed_command(self, command: str) -> None:
        """Add a command to the list of allowed commands.
        
        Args:
            command: The command to allow
        """
        if command not in self.allowed_commands:
            self.allowed_commands.append(command)

    def remove_allowed_command(self, command: str) -> None:
        """Remove a command from the list of allowed commands.
        
        Args:
            command: The command to disallow
        """
        if command in self.allowed_commands and command not in ["ls", "cat", "grep", "find"]:
            self.allowed_commands.remove(command)

    def set_working_directory(self, directory: str) -> None:
        """Set the working directory for command execution.
        
        Args:
            directory: The new working directory
        """
        if not os.path.isabs(directory):
            directory = os.path.join(self.working_directory, directory)
        self.working_directory = directory

    def set_timeout(self, timeout: int) -> None:
        """Set the command execution timeout.
        
        Args:
            timeout: The new timeout in seconds
        """
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")
        self.timeout = timeout

    def set_max_output_size(self, size: int) -> None:
        """Set the maximum allowed output size.
        
        Args:
            size: The new maximum size in bytes
        """
        if size < 1024:  # Minimum 1KB
            raise ValueError("Maximum output size must be at least 1KB")
        self.max_output_size = size 