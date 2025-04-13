"""A2A Task Management

This module implements task lifecycle management for the A2A protocol.
"""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from .types import (
    Artifact,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

logger = logging.getLogger(__name__)


class TaskManager:
    """Base class for A2A task managers."""
    
    def __init__(self):
        """Initialize the task manager."""
        self.tasks: dict[str, Task] = {}
        self.task_subscribers: dict[str, set[asyncio.Queue]] = {}
    
    async def process_task(self, params: TaskSendParams) -> Task:
        """Process a task.
        
        Args:
            params: The task parameters
            
        Returns:
            The task
        """
        # Get or create task ID
        task_id = params.id or str(uuid.uuid4())
        
        # Check if the task already exists
        if task_id in self.tasks:
            # Update existing task
            task = self.tasks[task_id]
            
            # Update task history
            if task.history is None:
                task.history = []
            task.history.append(params.message)
            
            # Update task status
            task.status = TaskStatus(
                state=TaskState.WORKING,
                message=params.message,
                timestamp=datetime.utcnow().isoformat(),
            )
            
            # Notify subscribers
            await self._notify_status_update(task)
            
            # Process the task
            await self._process_task_message(task, params.message)
            
            return task
        
        # Create a new task
        task = Task(
            id=task_id,
            session_id=params.session_id,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                message=params.message,
                timestamp=datetime.utcnow().isoformat(),
            ),
            history=[params.message] if params.history_length else None,
            metadata=params.metadata,
        )
        
        # Store the task
        self.tasks[task_id] = task
        
        # Update task status to working
        task.status = TaskStatus(
            state=TaskState.WORKING,
            message=params.message,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Notify subscribers
        await self._notify_status_update(task)
        
        # Process the task
        await self._process_task_message(task, params.message)
        
        return task
    
    async def get_task(self, task_id: str, history_length: int | None = None) -> Task:
        """Get a task.
        
        Args:
            task_id: The task ID
            history_length: The number of history items to include
            
        Returns:
            The task
            
        Raises:
            KeyError: If the task is not found
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Apply history length limit if specified
        if history_length is not None and task.history:
            task.history = task.history[-history_length:]
        
        return task
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The updated task
            
        Raises:
            KeyError: If the task is not found
            ValueError: If the task is not cancelable
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Check if the task is in a final state
        if task.status.state in [TaskState.COMPLETED, TaskState.CANCELED, TaskState.FAILED]:
            raise ValueError(f"Task is not cancelable: {task_id}")
        
        # Update task status
        task.status = TaskStatus(
            state=TaskState.CANCELED,
            message=task.status.message,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Notify subscribers
        await self._notify_status_update(task)
        
        return task
    
    async def subscribe_to_task(self, task_id: str) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        """Subscribe to task updates.
        
        Args:
            task_id: The task ID
            
        Yields:
            Task status and artifact update events
            
        Raises:
            KeyError: If the task is not found
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        # Create a queue for this subscriber
        queue = asyncio.Queue()
        
        # Add the queue to the subscribers for this task
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(queue)
        
        try:
            # Yield events from the queue
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        
        finally:
            # Remove the queue from the subscribers
            if task_id in self.task_subscribers:
                self.task_subscribers[task_id].discard(queue)
                if not self.task_subscribers[task_id]:
                    del self.task_subscribers[task_id]
    
    async def update_task_status(
        self,
        task_id: str,
        state: TaskState,
        message: Message | None = None,
    ) -> Task:
        """Update a task's status.
        
        Args:
            task_id: The task ID
            state: The new task state
            message: The message associated with the status update
            
        Returns:
            The updated task
            
        Raises:
            KeyError: If the task is not found
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Update task status
        task.status = TaskStatus(
            state=state,
            message=message or task.status.message,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Update task history if a message is provided
        if message and task.history is not None:
            task.history.append(message)
        
        # Notify subscribers
        await self._notify_status_update(task)
        
        return task
    
    async def add_task_artifact(
        self,
        task_id: str,
        artifact: Artifact,
    ) -> Task:
        """Add an artifact to a task.
        
        Args:
            task_id: The task ID
            artifact: The artifact to add
            
        Returns:
            The updated task
            
        Raises:
            KeyError: If the task is not found
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        
        task = self.tasks[task_id]
        
        # Initialize artifacts list if needed
        if task.artifacts is None:
            task.artifacts = []
        
        # Check if we should append to an existing artifact
        if artifact.append and artifact.index < len(task.artifacts):
            existing_artifact = task.artifacts[artifact.index]
            
            # Append parts to the existing artifact
            existing_artifact.parts.extend(artifact.parts)
            
            # Update other fields
            if artifact.name:
                existing_artifact.name = artifact.name
            if artifact.description:
                existing_artifact.description = artifact.description
            if artifact.metadata:
                existing_artifact.metadata = artifact.metadata or {}
                existing_artifact.metadata.update(artifact.metadata)
            
            # Set last_chunk if this is the final chunk
            if artifact.last_chunk:
                existing_artifact.last_chunk = True
            
            # Notify subscribers
            await self._notify_artifact_update(task, existing_artifact)
        
        else:
            # Add the new artifact
            task.artifacts.append(artifact)
            
            # Notify subscribers
            await self._notify_artifact_update(task, artifact)
        
        return task
    
    async def _notify_status_update(self, task: Task):
        """Notify subscribers of a task status update.
        
        Args:
            task: The task
        """
        if task.id not in self.task_subscribers:
            return
        
        # Create the event
        event = TaskStatusUpdateEvent(
            id=task.id,
            status=task.status,
            final=task.status.state in [
                TaskState.COMPLETED,
                TaskState.CANCELED,
                TaskState.FAILED,
            ],
        )
        
        # Notify all subscribers
        for queue in self.task_subscribers[task.id]:
            await queue.put(event)
        
        # If this is the final update, signal the end of the stream
        if event.final:
            for queue in self.task_subscribers[task.id]:
                await queue.put(None)
            del self.task_subscribers[task.id]
    
    async def _notify_artifact_update(self, task: Task, artifact: Artifact):
        """Notify subscribers of a task artifact update.
        
        Args:
            task: The task
            artifact: The artifact
        """
        if task.id not in self.task_subscribers:
            return
        
        # Create the event
        event = TaskArtifactUpdateEvent(
            id=task.id,
            artifact=artifact,
            final=False,
        )
        
        # Notify all subscribers
        for queue in self.task_subscribers[task.id]:
            await queue.put(event)
    
    async def _process_task_message(self, task: Task, message: Message):
        """Process a task message.
        
        This method should be overridden by subclasses to implement task processing.
        
        Args:
            task: The task
            message: The message to process
        """
        # Default implementation just completes the task with a simple response
        await self.update_task_status(
            task.id,
            TaskState.COMPLETED,
            Message(
                role="agent",
                parts=[
                    TextPart(
                        type="text",
                        text="Task processed successfully.",
                    ),
                ],
            ),
        )


class InMemoryTaskManager(TaskManager):
    """In-memory implementation of the A2A task manager."""
    
    async def _process_task_message(self, task: Task, message: Message):
        """Process a task message.
        
        This implementation simply echoes the message back as an artifact.
        
        Args:
            task: The task
            message: The message to process
        """
        # Create an artifact from the message
        artifact = Artifact(
            name="Echo",
            description="Echo of the input message",
            parts=message.parts,
        )
        
        # Add the artifact to the task
        await self.add_task_artifact(task.id, artifact)
        
        # Complete the task
        await self.update_task_status(
            task.id,
            TaskState.COMPLETED,
            Message(
                role="agent",
                parts=[
                    TextPart(
                        type="text",
                        text="Task processed successfully.",
                    ),
                ],
            ),
        )