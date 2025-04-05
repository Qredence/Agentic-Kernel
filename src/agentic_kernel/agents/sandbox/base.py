"""Base class for sandbox implementations."""

import abc
from typing import Dict, Any, Optional


class Sandbox(abc.ABC):
    """Abstract base class for sandbox implementations.
    
    This class defines the interface that all sandbox implementations must adhere to.
    Sandboxes provide secure environments for executing commands and code.
    """
    
    @abc.abstractmethod
    async def execute_command(
        self,
        command: str,
        timeout: int = 30,
        working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command within the sandbox.
        
        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds
            working_dir: Working directory for command execution
            
        Returns:
            A dictionary containing:
                - status: Exit code (0 for success)
                - output: Command standard output
                - error: Command standard error
        """
        pass
    
    @abc.abstractmethod
    async def ensure_started(self) -> bool:
        """Ensure the sandbox environment is started and ready.
        
        Returns:
            True if the sandbox is successfully started or already running
        """
        pass
    
    @abc.abstractmethod
    async def cleanup(self) -> None:
        """Clean up the sandbox environment."""
        pass
    
    @abc.abstractmethod
    async def reset(self) -> bool:
        """Reset the sandbox to a clean state.
        
        Returns:
            True if the sandbox was successfully reset
        """
        pass
    
    @property
    @abc.abstractmethod
    def is_running(self) -> bool:
        """Check if the sandbox is currently running.
        
        Returns:
            True if the sandbox is running, False otherwise
        """
        pass 