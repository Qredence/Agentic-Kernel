# A2A Agent Implementation Style Guide

## Introduction

This document provides guidelines and best practices for implementing agents that are compatible with the A2A (
Agent-to-Agent) protocol in the Agentic Kernel system. Following these guidelines will help ensure that your agents are
robust, maintainable, and interoperable with other agents in the ecosystem.

## Table of Contents

1. [General Principles](#general-principles)
2. [Code Organization](#code-organization)
3. [Agent Interface Design](#agent-interface-design)
4. [Error Handling](#error-handling)
5. [Asynchronous Programming](#asynchronous-programming)
6. [Task Processing](#task-processing)
7. [Message Handling](#message-handling)
8. [Artifact Management](#artifact-management)
9. [Testing A2A Agents](#testing-a2a-agents)
10. [Documentation](#documentation)
11. [Examples](#examples)

## General Principles

When implementing A2A-compatible agents, follow these general principles:

1. **Single Responsibility**: Each agent should have a clear, focused purpose
2. **Interoperability**: Design agents to work well with other agents
3. **Robustness**: Handle errors gracefully and recover from failures
4. **Scalability**: Design for performance under load
5. **Maintainability**: Write clean, well-documented code
6. **Security**: Implement proper authentication and authorization
7. **Testability**: Design agents to be easily testable

## Code Organization

Organize your agent code according to these guidelines:

### Directory Structure

```
my_agent/
├── __init__.py
├── agent.py           # Main agent implementation
├── config.py          # Configuration handling
├── server.py          # A2A server implementation
├── task_manager.py    # Task management logic
├── utils/             # Utility functions
│   ├── __init__.py
│   └── helpers.py
├── models/            # Data models
│   ├── __init__.py
│   └── data_models.py
├── services/          # External service integrations
│   ├── __init__.py
│   └── external_api.py
└── tests/             # Unit and integration tests
    ├── __init__.py
    ├── test_agent.py
    └── test_task_manager.py
```

### Module Organization

Each module should have a clear purpose and follow this structure:

1. Import statements (grouped by standard library, third-party, and local imports)
2. Constants and configuration
3. Class and function definitions
4. Main execution block (if applicable)

Example:

```python
"""
MyAgent - An A2A-compatible agent for specific tasks.

This module implements an agent that can perform specific tasks
using the A2A protocol.
"""

# Standard library imports
import asyncio
import logging
from typing import Dict, List, Optional, Any

# Third-party imports
from pydantic import BaseModel

# Local imports
from .config import AgentConfig
from .models.data_models import TaskResult
from .utils.helpers import format_response

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Class definitions
class MyAgent:
    """An A2A-compatible agent for specific tasks."""
    
    def __init__(self, config: AgentConfig):
        """Initialize the agent with the given configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    # ... rest of the class implementation

# Main execution (if applicable)
if __name__ == "__main__":
    config = AgentConfig.from_env()
    agent = MyAgent(config)
    asyncio.run(agent.start())
```

## Agent Interface Design

Design your agent interfaces according to these guidelines:

### Base Agent Class

Extend the base `BaseAgent` class to ensure compatibility with the Agentic Kernel system:

```python
from agentic_kernel.agents.base_agent import BaseAgent
from agentic_kernel.communication.a2a.types import Task, Message

class MyCustomAgent(BaseAgent):
    """A custom A2A-compatible agent."""
    
    def __init__(self, name: str, description: str, version: str):
        super().__init__()
        self.name = name
        self.description = description
        self.version = version
        
    async def execute(self, task: Task) -> Task:
        """Execute a task."""
        # Implement task execution logic
        return task
```

### Public Methods

Design public methods with clear signatures and documentation:

```python
async def process_data(
    self,
    data: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None
) -> TaskResult:
    """
    Process the given data according to the specified options.
    
    Args:
        data: The data to process
        options: Optional processing options
        
    Returns:
        A TaskResult containing the processed data
        
    Raises:
        ValueError: If the data is invalid
        ProcessingError: If processing fails
    """
    # Method implementation
```

### Method Naming

Use consistent method naming conventions:

- `get_*`: Methods that retrieve data
- `set_*`: Methods that update data
- `create_*`: Methods that create new resources
- `delete_*`: Methods that remove resources
- `process_*`: Methods that process data
- `handle_*`: Methods that handle events or messages
- `validate_*`: Methods that validate data

## Error Handling

Implement robust error handling in your agents:

### Error Types

Define specific error types for different failure scenarios:

```python
class AgentError(Exception):
    """Base class for all agent errors."""
    pass

class ConfigurationError(AgentError):
    """Error raised when there is a configuration issue."""
    pass

class TaskProcessingError(AgentError):
    """Error raised when task processing fails."""
    pass

class ExternalServiceError(AgentError):
    """Error raised when an external service call fails."""
    pass
```

### Error Handling Pattern

Use this pattern for handling errors:

```python
async def process_task_message(self, task: Task, message: Message) -> None:
    """Process a task message."""
    try:
        # Validate inputs
        self._validate_message(message)
        
        # Process the message
        result = await self._process_message_content(message)
        
        # Create artifact from result
        artifact = self._create_artifact_from_result(result)
        
        # Add artifact to task
        await self.add_task_artifact(task.id, artifact)
        
        # Complete the task
        await self.update_task_status(task.id, TaskState.COMPLETED)
    
    except ValueError as e:
        # Handle validation errors
        self.logger.warning(f"Validation error in task {task.id}: {str(e)}")
        await self._fail_task_with_error(task.id, f"Invalid input: {str(e)}")
    
    except ExternalServiceError as e:
        # Handle external service errors
        self.logger.error(f"External service error in task {task.id}: {str(e)}")
        await self._fail_task_with_error(task.id, f"External service error: {str(e)}")
    
    except Exception as e:
        # Handle unexpected errors
        self.logger.exception(f"Unexpected error in task {task.id}: {str(e)}")
        await self._fail_task_with_error(task.id, f"Internal error: {str(e)}")
```

### Retry Logic

Implement retry logic for transient failures:

```python
async def call_external_service_with_retry(self, service_call, *args, **kwargs):
    """Call an external service with retry logic."""
    max_retries = self.config.max_retries
    retry_delay = self.config.retry_delay
    
    for attempt in range(max_retries + 1):
        try:
            return await service_call(*args, **kwargs)
        
        except TransientError as e:
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                self.logger.warning(
                    f"Transient error: {str(e)}. Retrying in {wait_time}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
            else:
                self.logger.error(f"Max retries exceeded: {str(e)}")
                raise
```

## Asynchronous Programming

Follow these guidelines for asynchronous programming:

### Use Async/Await Consistently

Use `async`/`await` consistently throughout your code:

```python
async def process_task(self, task: Task) -> None:
    """Process a task asynchronously."""
    # Use await for all async operations
    result = await self._fetch_data(task.parameters)
    processed_result = await self._process_data(result)
    await self._store_result(task.id, processed_result)
```

### Avoid Blocking Operations

Avoid blocking operations in async code:

```python
# Bad - blocks the event loop
def process_data(self, data):
    time.sleep(1)  # Blocks the event loop
    return process_result

# Good - uses async sleep
async def process_data(self, data):
    await asyncio.sleep(1)  # Non-blocking
    return process_result
```

### Handle Concurrency Properly

Use appropriate concurrency controls:

```python
class ConcurrencyLimitedAgent(BaseAgent):
    """Agent with concurrency limits."""
    
    def __init__(self, max_concurrent_tasks=10):
        super().__init__()
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
    
    async def process_task(self, task: Task) -> None:
        """Process a task with concurrency control."""
        async with self.semaphore:
            await self._process_task_implementation(task)
```

## Task Processing

Follow these guidelines for task processing:

### Task State Management

Manage task states properly:

```python
async def process_task_message(self, task: Task, message: Message) -> None:
    """Process a task message with proper state management."""
    # Update task status to WORKING
    await self.update_task_status(task.id, TaskState.WORKING)
    
    try:
        # Process the task
        result = await self._process_message(message)
        
        # Create and add artifact
        artifact = self._create_artifact(result)
        await self.add_task_artifact(task.id, artifact)
        
        # Update task status to COMPLETED
        await self.update_task_status(task.id, TaskState.COMPLETED)
    
    except Exception as e:
        # Update task status to FAILED
        await self.update_task_status(
            task.id,
            TaskState.FAILED,
            Message(
                role="agent",
                parts=[
                    TextPart(
                        type="text",
                        text=f"Task failed: {str(e)}"
                    )
                ]
            )
        )
```

### Progress Reporting

Implement progress reporting for long-running tasks:

```python
async def process_large_task(self, task: Task, message: Message) -> None:
    """Process a large task with progress reporting."""
    total_steps = 10
    
    # Update task status to WORKING
    await self.update_task_status(task.id, TaskState.WORKING)
    
    try:
        for step in range(total_steps):
            # Process one step
            result = await self._process_step(step, message)
            
            # Report progress
            progress_message = Message(
                role="agent",
                parts=[
                    TextPart(
                        type="text",
                        text=f"Processing step {step + 1}/{total_steps}"
                    )
                ]
            )
            await self.update_task_status(task.id, TaskState.WORKING, progress_message)
            
            # Add intermediate artifact if available
            if result:
                artifact = self._create_artifact(result, f"step_{step + 1}")
                await self.add_task_artifact(task.id, artifact)
        
        # Update task status to COMPLETED
        await self.update_task_status(task.id, TaskState.COMPLETED)
    
    except Exception as e:
        # Update task status to FAILED
        await self.update_task_status(task.id, TaskState.FAILED)
```

## Message Handling

Follow these guidelines for message handling:

### Message Validation

Validate incoming messages:

```python
def _validate_message(self, message: Message) -> None:
    """Validate a message."""
    if not message.parts:
        raise ValueError("Message has no parts")
    
    for part in message.parts:
        if hasattr(part, "text") and not part.text:
            raise ValueError("Text part has empty text")
        elif hasattr(part, "file") and not (part.file.bytes or part.file.uri):
            raise ValueError("File part has no content")
```

### Message Parsing

Parse message content consistently:

```python
def _extract_text_from_message(self, message: Message) -> str:
    """Extract text content from a message."""
    text_parts = []
    
    for part in message.parts:
        if hasattr(part, "text"):
            text_parts.append(part.text)
    
    return "\n".join(text_parts)

def _extract_files_from_message(self, message: Message) -> List[FileContent]:
    """Extract file content from a message."""
    files = []
    
    for part in message.parts:
        if hasattr(part, "file"):
            files.append(part.file)
    
    return files
```

## Artifact Management

Follow these guidelines for artifact management:

### Creating Artifacts

Create artifacts with clear structure:

```python
def _create_text_artifact(self, text: str, name: str = "result") -> Artifact:
    """Create a text artifact."""
    return Artifact(
        name=name,
        description=f"Text result: {name}",
        parts=[
            TextPart(
                type="text",
                text=text
            )
        ]
    )

def _create_file_artifact(self, file_content: FileContent, name: str = "file_result") -> Artifact:
    """Create a file artifact."""
    return Artifact(
        name=name,
        description=f"File result: {name}",
        parts=[
            FilePart(
                type="file",
                file=file_content
            )
        ]
    )
```

### Streaming Artifacts

Implement streaming for large artifacts:

```python
async def _stream_large_result(self, task_id: str, result_generator, chunk_size: int = 1000):
    """Stream a large result as multiple artifact chunks."""
    chunk_index = 0
    
    async for chunk in result_generator:
        # Create artifact for this chunk
        artifact = Artifact(
            name=f"result_chunk_{chunk_index}",
            description=f"Result chunk {chunk_index}",
            parts=[
                TextPart(
                    type="text",
                    text=chunk
                )
            ],
            index=0,  # Always use the same index for appending
            append=chunk_index > 0,  # Append after the first chunk
            last_chunk=(chunk_index == chunk_size - 1)  # Mark the last chunk
        )
        
        # Add the artifact to the task
        await self.add_task_artifact(task_id, artifact)
        
        chunk_index += 1
```

## Testing A2A Agents

Follow these guidelines for testing A2A agents:

### Unit Testing

Write unit tests for agent components:

```python
import pytest
from unittest.mock import AsyncMock, patch

from agentic_kernel.communication.a2a.types import Task, Message, TaskStatus, TaskState, TextPart

@pytest.fixture
def agent():
    """Create a test agent."""
    return MyCustomAgent("Test Agent", "Agent for testing", "1.0.0")

@pytest.mark.asyncio
async def test_process_message(agent):
    """Test message processing."""
    # Arrange
    message = Message(
        role="user",
        parts=[
            TextPart(
                type="text",
                text="Test message"
            )
        ]
    )
    
    # Act
    result = await agent._process_message(message)
    
    # Assert
    assert result is not None
    assert "Test message" in result
```

### Integration Testing

Write integration tests for end-to-end functionality:

```python
@pytest.mark.asyncio
async def test_task_execution():
    """Test end-to-end task execution."""
    # Create a client and server
    server = create_test_server()
    client = A2AClient("http://localhost:8000")
    
    try:
        # Start the server
        await server.start()
        
        # Send a task
        task_params = TaskSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Test task"
                    )
                ]
            )
        )
        task = await client.tasks_send(task_params)
        
        # Wait for task completion
        for _ in range(10):  # Timeout after 10 seconds
            task = await client.tasks_get(task.id)
            if task.status.state in [TaskState.COMPLETED, TaskState.FAILED]:
                break
            await asyncio.sleep(1)
        
        # Assert
        assert task.status.state == TaskState.COMPLETED
        assert task.artifacts is not None
        assert len(task.artifacts) > 0
    
    finally:
        # Clean up
        await server.stop()
        await client.close()
```

### Mocking External Dependencies

Mock external dependencies in tests:

```python
@pytest.mark.asyncio
async def test_external_service_integration(agent):
    """Test integration with external service."""
    # Arrange
    task = Task(
        id="test-task",
        status=TaskStatus(
            state=TaskState.SUBMITTED,
            timestamp="2023-01-01T00:00:00Z"
        )
    )
    message = Message(
        role="user",
        parts=[
            TextPart(
                type="text",
                text="Call external service"
            )
        ]
    )
    
    # Mock the external service
    with patch("my_agent.services.external_api.call_service") as mock_service:
        mock_service.return_value = AsyncMock(return_value={"result": "success"})
        
        # Act
        await agent.process_task_message(task, message)
        
        # Assert
        mock_service.assert_called_once()
        assert task.status.state == TaskState.COMPLETED
```

## Documentation

Follow these guidelines for documenting your A2A agents:

### Code Documentation

Document your code with clear docstrings:

```python
class MyAgent(BaseAgent):
    """
    A custom agent that processes specific types of data.
    
    This agent implements the A2A protocol and provides capabilities
    for processing and analyzing data in various formats.
    
    Attributes:
        name: The name of the agent
        version: The version of the agent
        config: The agent configuration
    """
    
    async def process_task_message(self, task: Task, message: Message) -> None:
        """
        Process a task message.
        
        This method handles the core task processing logic, extracting
        content from the message, processing it, and updating the task
        with the results.
        
        Args:
            task: The task to process
            message: The message containing the task instructions
            
        Raises:
            ValueError: If the message format is invalid
            ProcessingError: If processing fails
        """
        # Method implementation
```

### Agent Documentation

Create comprehensive documentation for your agent using the templates
in [Agent Capability Documentation Templates](agent_capability_documentation_templates.md).

## Examples

### Complete Agent Implementation

Here's an example of a complete A2A-compatible agent implementation:

```python
"""
TextProcessingAgent - An A2A-compatible agent for text processing.

This module implements an agent that can perform various text processing
tasks using the A2A protocol.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from agentic_kernel.agents.base_agent import BaseAgent
from agentic_kernel.communication.a2a.types import (
    Task,
    Message,
    TaskState,
    TaskStatus,
    Artifact,
    TextPart,
)

class TextProcessingError(Exception):
    """Error raised when text processing fails."""
    pass

class TextProcessingAgent(BaseAgent):
    """An A2A-compatible agent for text processing."""
    
    def __init__(
        self,
        name: str = "TextProcessor",
        description: str = "Agent for text processing tasks",
        version: str = "1.0.0",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the text processing agent.
        
        Args:
            name: The name of the agent
            description: A description of the agent
            version: The agent version
            config: Optional configuration parameters
        """
        super().__init__()
        self.name = name
        self.description = description
        self.version = version
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    async def process_task_message(self, task: Task, message: Message) -> None:
        """
        Process a task message.
        
        Args:
            task: The task to process
            message: The message containing the text to process
            
        Raises:
            ValueError: If the message format is invalid
            TextProcessingError: If text processing fails
        """
        try:
            # Validate the message
            self._validate_message(message)
            
            # Extract text from the message
            text = self._extract_text_from_message(message)
            
            # Update task status to WORKING
            await self.update_task_status(
                task.id,
                TaskState.WORKING,
                Message(
                    role="agent",
                    parts=[
                        TextPart(
                            type="text",
                            text="Processing text..."
                        )
                    ]
                )
            )
            
            # Process the text
            result = await self._process_text(text)
            
            # Create an artifact with the result
            artifact = Artifact(
                name="processed_text",
                description="Processed text result",
                parts=[
                    TextPart(
                        type="text",
                        text=result
                    )
                ]
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
                            text="Text processing completed successfully."
                        )
                    ]
                )
            )
        
        except ValueError as e:
            # Handle validation errors
            self.logger.warning(f"Validation error in task {task.id}: {str(e)}")
            await self._fail_task_with_error(task.id, f"Invalid input: {str(e)}")
        
        except TextProcessingError as e:
            # Handle processing errors
            self.logger.error(f"Processing error in task {task.id}: {str(e)}")
            await self._fail_task_with_error(task.id, f"Processing error: {str(e)}")
        
        except Exception as e:
            # Handle unexpected errors
            self.logger.exception(f"Unexpected error in task {task.id}: {str(e)}")
            await self._fail_task_with_error(task.id, f"Internal error: {str(e)}")
    
    def _validate_message(self, message: Message) -> None:
        """
        Validate a message.
        
        Args:
            message: The message to validate
            
        Raises:
            ValueError: If the message is invalid
        """
        if not message.parts:
            raise ValueError("Message has no parts")
        
        has_text = False
        for part in message.parts:
            if hasattr(part, "text") and part.text:
                has_text = True
                break
        
        if not has_text:
            raise ValueError("Message has no text content")
    
    def _extract_text_from_message(self, message: Message) -> str:
        """
        Extract text content from a message.
        
        Args:
            message: The message to extract text from
            
        Returns:
            The extracted text
        """
        text_parts = []
        
        for part in message.parts:
            if hasattr(part, "text"):
                text_parts.append(part.text)
        
        return "\n".join(text_parts)
    
    async def _process_text(self, text: str) -> str:
        """
        Process text.
        
        Args:
            text: The text to process
            
        Returns:
            The processed text
            
        Raises:
            TextProcessingError: If processing fails
        """
        try:
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Perform text processing (example: convert to uppercase)
            processed_text = text.upper()
            
            return processed_text
        
        except Exception as e:
            raise TextProcessingError(f"Failed to process text: {str(e)}")
    
    async def _fail_task_with_error(self, task_id: str, error_message: str) -> None:
        """
        Fail a task with an error message.
        
        Args:
            task_id: The ID of the task to fail
            error_message: The error message
        """
        await self.update_task_status(
            task_id,
            TaskState.FAILED,
            Message(
                role="agent",
                parts=[
                    TextPart(
                        type="text",
                        text=error_message
                    )
                ]
            )
        )
```

By following this style guide, you'll create A2A-compatible agents that are robust, maintainable, and interoperable with
other agents in the Agentic Kernel ecosystem.