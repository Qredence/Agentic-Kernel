"""Simple A2A Server Implementation

This module provides a simple implementation of the A2A server that uses the
task manager to handle tasks.
"""

import logging

from .server import A2AServer
from .task import InMemoryTaskManager, TaskManager
from .types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

logger = logging.getLogger(__name__)


class SimpleA2AServer(A2AServer):
    """Simple implementation of the A2A server."""
    
    def __init__(
        self,
        name: str,
        description: str | None = None,
        version: str = "1.0.0",
        skills: list[AgentSkill] | None = None,
        task_manager: TaskManager | None = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        cors_origins: list[str] = None,
        debug: bool = False,
    ):
        """Initialize the simple A2A server.
        
        Args:
            name: The name of the agent
            description: The description of the agent
            version: The version of the agent
            skills: The skills of the agent
            task_manager: The task manager to use
            host: The host to bind to
            port: The port to bind to
            cors_origins: List of allowed CORS origins
            debug: Whether to enable debug mode
        """
        # Create a default agent card
        agent_card = AgentCard(
            name=name,
            description=description or f"Simple A2A server: {name}",
            url=f"http://{host}:{port}",
            version=version,
            capabilities=AgentCapabilities(
                streaming=True,
                push_notifications=False,
                state_transition_history=True,
            ),
            default_input_modes=["text"],
            default_output_modes=["text"],
            skills=skills or [
                AgentSkill(
                    id="echo",
                    name="Echo",
                    description="Echoes the input message back as an artifact",
                    input_modes=["text"],
                    output_modes=["text"],
                ),
            ],
        )
        
        # Initialize the A2A server
        super().__init__(
            agent_card=agent_card,
            host=host,
            port=port,
            cors_origins=cors_origins,
            debug=debug,
        )
        
        # Initialize the task manager
        self.task_manager = task_manager or InMemoryTaskManager()
    
    # Implement the abstract methods from A2AServer
    
    async def process_task(self, params):
        """Process a task.
        
        Args:
            params: The task parameters
            
        Returns:
            The task
        """
        return await self.task_manager.process_task(params)
    
    async def get_task(self, task_id, history_length=None):
        """Get a task.
        
        Args:
            task_id: The task ID
            history_length: The number of history items to include
            
        Returns:
            The task
            
        Raises:
            A2AErrorCode.TASK_NOT_FOUND: If the task is not found
        """
        try:
            return await self.task_manager.get_task(task_id, history_length)
        except KeyError:
            raise ValueError(f"Task not found: {task_id}") from None
    
    async def cancel_task(self, task_id):
        """Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The updated task
            
        Raises:
            A2AErrorCode.TASK_NOT_FOUND: If the task is not found
            A2AErrorCode.TASK_NOT_CANCELABLE: If the task is not cancelable
        """
        try:
            return await self.task_manager.cancel_task(task_id)
        except KeyError:
            raise ValueError(f"Task not found: {task_id}") from None
        except ValueError:
            raise ValueError(f"Task is not cancelable: {task_id}") from None
    
    async def subscribe_to_task(self, task_id):
        """Subscribe to task updates.
        
        Args:
            task_id: The task ID
            
        Yields:
            Task status and artifact update events
            
        Raises:
            A2AErrorCode.TASK_NOT_FOUND: If the task is not found
        """
        try:
            async for event in self.task_manager.subscribe_to_task(task_id):
                yield event
        except KeyError:
            raise ValueError(f"Task not found: {task_id}") from None


def create_simple_server(
    name: str,
    description: str | None = None,
    version: str = "1.0.0",
    skills: list[AgentSkill] | None = None,
    task_manager: TaskManager | None = None,
    host: str = "0.0.0.0",
    port: int = 8000,
    cors_origins: list[str] = None,
    debug: bool = False,
) -> SimpleA2AServer:
    """Create a simple A2A server.
    
    Args:
        name: The name of the agent
        description: The description of the agent
        version: The version of the agent
        skills: The skills of the agent
        task_manager: The task manager to use
        host: The host to bind to
        port: The port to bind to
        cors_origins: List of allowed CORS origins
        debug: Whether to enable debug mode
        
    Returns:
        A simple A2A server
    """
    return SimpleA2AServer(
        name=name,
        description=description,
        version=version,
        skills=skills,
        task_manager=task_manager,
        host=host,
        port=port,
        cors_origins=cors_origins,
        debug=debug,
    )