"""A2A Task Management

This module implements task lifecycle management for the A2A protocol.

The A2A protocol enables agents to communicate and collaborate with each other through
standardized task-based interactions. The TaskManager class in this module provides the
core functionality for managing the lifecycle of tasks, including:

1. Task Creation and Processing: Creating new tasks and processing task messages
2. Task Status Management: Updating and tracking task status
3. Artifact Management: Adding and retrieving task artifacts
4. Subscription Management: Enabling clients to subscribe to task updates
5. Notification System: Notifying subscribers of task status and artifact updates

The task lifecycle follows these states:
- SUBMITTED: Task has been submitted but processing hasn't started
- WORKING: Task is actively being processed
- INPUT_REQUIRED: Task requires additional input to continue
- COMPLETED: Task has been successfully completed
- CANCELED: Task has been canceled
- FAILED: Task has failed due to an error

Agent interaction through the A2A protocol typically follows this pattern:
1. Client sends a task to an agent via tasks/send
2. Agent processes the task and updates its status
3. Agent adds artifacts (results) to the task
4. Agent completes the task
5. Client retrieves the task results

For long-running tasks, clients can subscribe to task updates using tasks/sendSubscribe
to receive real-time status and artifact updates.
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

        This method is the entry point for task processing in the A2A protocol.
        It handles both new task creation and continuation of existing tasks.

        The task processing flow:
        1. Get or create a task ID
        2. Check if the task already exists
           a. If it exists, update its history and status
           b. If it doesn't exist, create a new task
        3. Update the task status to WORKING
        4. Notify subscribers of the status update
        5. Process the task message (implemented by subclasses)

        Args:
            params: The task parameters including message, session ID, and metadata

        Returns:
            The task object with its current state
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

        This method enables real-time streaming of task updates to clients.
        It's a key component of the A2A protocol's streaming capability,
        allowing clients to receive incremental updates for long-running tasks.

        The subscription flow:
        1. Create an async queue for this subscriber
        2. Add the queue to the set of subscribers for this task
        3. Yield events from the queue as they arrive
        4. Clean up the subscription when the client disconnects or the task completes

        Events are sent to subscribers when:
        - Task status changes (via _notify_status_update)
        - Task artifacts are added or updated (via _notify_artifact_update)

        Args:
            task_id: The task ID to subscribe to

        Yields:
            Task status and artifact update events as they occur

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

        This method is used to transition a task between different states in its lifecycle.
        It's a critical part of the agent interaction protocol, as it communicates the
        progress and state of task execution to clients and other agents.

        Status transitions typically follow this pattern:
        SUBMITTED -> WORKING -> (INPUT_REQUIRED) -> COMPLETED/FAILED/CANCELED

        Each status update:
        1. Updates the task's status object with the new state
        2. Adds the message to the task history (if provided)
        3. Notifies all subscribers of the status change

        Final states (COMPLETED, FAILED, CANCELED) trigger special handling in the
        notification system to signal the end of the task lifecycle.

        Args:
            task_id: The task ID to update
            state: The new task state (from TaskState enum)
            message: Optional message associated with the status update

        Returns:
            The updated task object

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

        Artifacts are the primary mechanism for agents to return results to clients.
        They can contain various types of content (text, files, structured data) and
        can be added incrementally for streaming responses.

        This method handles two cases:
        1. Adding a new artifact to the task
        2. Appending to an existing artifact (for streaming/chunked responses)

        The artifact handling flow:
        1. Initialize the artifacts list if it doesn't exist
        2. Check if we should append to an existing artifact (based on append flag and index)
           a. If appending, update the existing artifact with new parts and metadata
           b. If not appending, add the new artifact to the list
        3. Notify subscribers of the artifact update

        Streaming artifacts typically use the append flag and last_chunk flag to indicate
        when a chunked artifact is complete.

        Args:
            task_id: The task ID to add the artifact to
            artifact: The artifact to add or append

        Returns:
            The updated task object

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

        This internal method is called whenever a task's status changes.
        It creates a TaskStatusUpdateEvent and sends it to all subscribers.

        The notification flow:
        1. Check if there are any subscribers for this task
        2. Create a TaskStatusUpdateEvent with the current status
        3. Set the 'final' flag if the task is in a terminal state
        4. Send the event to all subscribers' queues
        5. If this is a final update, send None to signal end of stream and clean up

        This is a key part of the real-time communication mechanism in the A2A protocol,
        enabling clients to receive immediate updates about task progress.

        Args:
            task: The task whose status has changed
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

        This internal method is called whenever an artifact is added or updated.
        It creates a TaskArtifactUpdateEvent and sends it to all subscribers.

        The notification flow:
        1. Check if there are any subscribers for this task
        2. Create a TaskArtifactUpdateEvent with the artifact
        3. Send the event to all subscribers' queues

        This method enables streaming of incremental results to clients,
        which is particularly useful for long-running tasks that produce
        results gradually.

        Args:
            task: The task that the artifact belongs to
            artifact: The artifact that was added or updated
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

        This method is the core of agent-specific task processing logic.
        It should be overridden by subclasses to implement custom behavior.

        The agent interaction pattern:
        1. Agent receives a task message via this method
        2. Agent processes the message according to its capabilities
        3. Agent updates task status as it progresses
        4. Agent adds artifacts (results) to the task
        5. Agent completes the task by setting its status to COMPLETED

        This default implementation simply completes the task with a generic message.
        Real agent implementations would perform domain-specific processing here.

        Args:
            task: The task to process
            message: The message containing the task instructions
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
    """In-memory implementation of the A2A task manager.

    This class provides a simple implementation of the TaskManager that stores
    all tasks in memory. It's suitable for development, testing, and simple
    deployments, but doesn't provide persistence across restarts.

    The implementation demonstrates the basic pattern for creating custom
    task managers:
    1. Extend the TaskManager base class
    2. Override the _process_task_message method to implement custom processing logic

    For production systems, you might want to implement a persistent task manager
    that stores tasks in a database or other persistent storage.
    """

    async def _process_task_message(self, task: Task, message: Message):
        """Process a task message.

        This implementation demonstrates a simple echo agent that:
        1. Takes the input message
        2. Creates an artifact containing the same content
        3. Adds the artifact to the task
        4. Completes the task with a success message

        This serves as a minimal example of the agent interaction pattern:
        - Receive input (message)
        - Process it (in this case, just echo it back)
        - Produce output (artifact)
        - Signal completion (update status to COMPLETED)

        Real agents would implement more complex processing logic here,
        potentially calling external services, performing computations,
        or coordinating with other agents.

        Args:
            task: The task to process
            message: The message to echo back
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
