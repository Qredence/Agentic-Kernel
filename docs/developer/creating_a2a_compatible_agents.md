# Creating A2A-Compatible Agents

## Introduction

This guide provides detailed instructions for creating new agent types that are compatible with the A2A (Agent-to-Agent)
protocol in the Agentic Kernel system. By following these steps, you can create agents that can seamlessly communicate
and collaborate with other agents in the system.

## Table of Contents

1. [Understanding A2A Compatibility](#understanding-a2a-compatibility)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Agent Card Definition](#agent-card-definition)
5. [Implementing Required Methods](#implementing-required-methods)
6. [Task Processing](#task-processing)
7. [Error Handling](#error-handling)
8. [Testing Your Agent](#testing-your-agent)
9. [Advanced Topics](#advanced-topics)
10. [Examples](#examples)

## Understanding A2A Compatibility

A2A compatibility means that your agent can:

1. Advertise its capabilities through an Agent Card
2. Receive and process tasks from other agents
3. Return results in a standardized format
4. Handle errors gracefully
5. Support streaming updates for long-running tasks (optional)
6. Send and receive push notifications (optional)

The A2A protocol is built on JSON-RPC 2.0 and defines a set of methods that agents must implement to be compatible.

## Prerequisites

Before creating an A2A-compatible agent, you should have:

1. A basic understanding of the A2A protocol (see [Agent Communication Protocols](agent_communication_protocols.md))
2. Familiarity with the Agentic Kernel codebase
3. Python 3.9 or later
4. The Agentic Kernel package installed

## Step-by-Step Guide

### 1. Create a New Agent Class

Start by creating a new agent class that extends the `BaseAgent` class:

```python
from agentic_kernel.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    """A custom agent that implements the A2A protocol."""
    
    def __init__(self, name: str, description: str, version: str):
        super().__init__()
        self.name = name
        self.description = description
        self.version = version
```

### 2. Define Agent Capabilities

Define the capabilities of your agent by implementing the `get_capabilities` method:

```python
from agentic_kernel.communication.a2a.types import AgentCapabilities

def get_capabilities(self) -> AgentCapabilities:
    """Return the capabilities of this agent."""
    return AgentCapabilities(
        streaming=True,
        push_notifications=False,
        state_transition_history=True
    )
```

### 3. Define Agent Skills

Define the skills that your agent provides by implementing the `get_skills` method:

```python
from agentic_kernel.communication.a2a.types import AgentSkill

def get_skills(self) -> list[AgentSkill]:
    """Return the skills provided by this agent."""
    return [
        AgentSkill(
            id="skill1",
            name="Example Skill",
            description="An example skill provided by this agent",
            tags=["example", "demo"],
            examples=["Example usage of this skill"],
            input_modes=["text"],
            output_modes=["text"]
        )
    ]
```

### 4. Create an A2A Server

Create an A2A server that will handle incoming requests:

```python
from agentic_kernel.communication.a2a.server import A2AServer
from agentic_kernel.communication.a2a.task import InMemoryTaskManager

# Create a task manager
task_manager = InMemoryTaskManager()

# Create an A2A server
server = A2AServer(
    name=self.name,
    description=self.description,
    version=self.version,
    task_manager=task_manager,
    capabilities=self.get_capabilities(),
    skills=self.get_skills(),
    default_input_modes=["text"],
    default_output_modes=["text"]
)
```

### 5. Implement Task Processing

Implement the logic for processing tasks by overriding the `_process_task_message` method in your task manager:

```python
from agentic_kernel.communication.a2a.task import TaskManager
from agentic_kernel.communication.a2a.types import Task, Message, TaskState, Artifact, TextPart

class MyTaskManager(TaskManager):
    """Custom task manager for processing tasks."""
    
    async def _process_task_message(self, task: Task, message: Message) -> None:
        """Process a task message."""
        # Update task status to WORKING
        await self.update_task_status(task.id, TaskState.WORKING)
        
        try:
            # Process the message
            result = await self._process_message(message)
            
            # Create an artifact with the result
            artifact = Artifact(
                name="result",
                parts=[
                    TextPart(
                        type="text",
                        text=result
                    )
                ]
            )
            
            # Add the artifact to the task
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
    
    async def _process_message(self, message: Message) -> str:
        """Process a message and return a result."""
        # Implement your custom logic here
        return "Hello, A2A!"
```

### 6. Start the Server

Start the A2A server to begin accepting requests:

```python
# Start the server
await server.start()
```

## Agent Card Definition

The Agent Card is a key component of A2A compatibility. It advertises the capabilities, skills, and other metadata of
your agent to other agents in the system.

Here's an example of a complete Agent Card:

```python
from agentic_kernel.communication.a2a.types import (
    AgentCard,
    AgentProvider,
    AgentCapabilities,
    AgentAuthentication,
    AgentSkill
)

def get_agent_card(self) -> AgentCard:
    """Return the Agent Card for this agent."""
    return AgentCard(
        name=self.name,
        description=self.description,
        url="http://localhost:8000",
        provider=AgentProvider(
            name="My Organization",
            url="https://example.com",
            logo_url="https://example.com/logo.png"
        ),
        version=self.version,
        documentation_url="https://example.com/docs",
        capabilities=self.get_capabilities(),
        authentication=AgentAuthentication(
            type="api_key",
            description="API key authentication",
            required=True,
            configuration={
                "header_name": "X-API-Key"
            }
        ),
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=self.get_skills()
    )
```

## Implementing Required Methods

To be fully A2A-compatible, your agent should implement the following methods:

1. `agent/getCard`: Returns the Agent Card
2. `tasks/send`: Sends a task to the agent
3. `tasks/get`: Gets information about a task
4. `tasks/cancel`: Cancels a task

The A2A server implementation in Agentic Kernel handles these methods for you, delegating to the task manager for
task-related operations.

## Task Processing

Task processing is the core functionality of an A2A-compatible agent. The task lifecycle typically follows these steps:

1. **Submission**: A task is submitted to the agent via the `tasks/send` method
2. **Processing**: The agent processes the task, updating its status as it progresses
3. **Completion**: The agent completes the task, providing results as artifacts
4. **Error Handling**: If an error occurs, the agent updates the task status to FAILED with an error message

Here's a more detailed example of task processing:

```python
async def _process_message(self, message: Message) -> str:
    """Process a message and return a result."""
    # Extract text from the message
    text = ""
    for part in message.parts:
        if hasattr(part, "text"):
            text += part.text
    
    # Process the text (this is where your agent's core logic goes)
    if "hello" in text.lower():
        return "Hello! How can I help you today?"
    elif "weather" in text.lower():
        return "I'm sorry, I don't have access to weather information."
    else:
        return "I received your message, but I'm not sure how to respond."
```

## Error Handling

Proper error handling is essential for A2A-compatible agents. When an error occurs during task processing, the agent
should:

1. Update the task status to FAILED
2. Provide an error message explaining what went wrong
3. Log the error for debugging purposes

Here's an example of error handling:

```python
try:
    # Process the message
    result = await self._process_message(message)
    
    # Create an artifact with the result
    # ...
    
except Exception as e:
    # Log the error
    logging.error(f"Error processing task {task.id}: {str(e)}")
    
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

## Testing Your Agent

To test your A2A-compatible agent, you can:

1. Create a test client that sends requests to your agent
2. Use the A2A client provided by Agentic Kernel
3. Create integration tests that simulate agent interactions

Here's an example of testing your agent using the A2A client:

```python
from agentic_kernel.communication.a2a.client import A2AClient
from agentic_kernel.communication.a2a.types import Message, TaskSendParams, TextPart

async def test_agent():
    # Create an A2A client
    client = A2AClient("http://localhost:8000")
    
    try:
        # Get the agent card
        agent_card = await client.get_agent_card()
        print(f"Agent name: {agent_card.name}")
        
        # Send a task
        task_params = TaskSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Hello, agent!"
                    )
                ]
            )
        )
        task = await client.tasks_send(task_params)
        print(f"Task ID: {task.id}")
        print(f"Task status: {task.status.state}")
        
        # Get the task result
        task = await client.tasks_get(task.id)
        print(f"Task status: {task.status.state}")
        
        if task.artifacts:
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if hasattr(part, "text"):
                        print(f"Result: {part.text}")
    
    finally:
        # Close the client
        await client.close()
```

## Advanced Topics

### Streaming Updates

To support streaming updates for long-running tasks, you can:

1. Update the task status periodically
2. Add artifacts incrementally as they become available
3. Use the `tasks/sendSubscribe` method for clients to receive streaming updates

Here's an example of streaming updates:

```python
async def _process_task_message(self, task: Task, message: Message) -> None:
    """Process a task message with streaming updates."""
    # Update task status to WORKING
    await self.update_task_status(task.id, TaskState.WORKING)
    
    try:
        # Process the message in chunks
        for i in range(5):
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Create an artifact with the intermediate result
            artifact = Artifact(
                name=f"chunk_{i}",
                parts=[
                    TextPart(
                        type="text",
                        text=f"Processing chunk {i+1}/5..."
                    )
                ],
                append=True,
                last_chunk=(i == 4)
            )
            
            # Add the artifact to the task
            await self.add_task_artifact(task.id, artifact)
        
        # Create a final artifact with the result
        artifact = Artifact(
            name="result",
            parts=[
                TextPart(
                    type="text",
                    text="Processing complete!"
                )
            ]
        )
        
        # Add the artifact to the task
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

### Push Notifications

To support push notifications, you need to:

1. Set `push_notifications=True` in your agent's capabilities
2. Handle the `push_notification` parameter in task requests
3. Send notifications to the specified endpoint when task status changes

Here's an example of handling push notifications:

```python
async def process_task(self, params: TaskSendParams) -> Task:
    """Process a task with push notifications."""
    # Create or update the task
    task = await super().process_task(params)
    
    # Store the push notification configuration if provided
    if params.push_notification:
        self._push_notification_configs[task.id] = params.push_notification
    
    return task

async def _notify_status_update(self, task: Task) -> None:
    """Notify subscribers of a task status update."""
    # Notify subscribers via the standard mechanism
    await super()._notify_status_update(task)
    
    # Send push notification if configured
    if task.id in self._push_notification_configs:
        await self._send_push_notification(
            self._push_notification_configs[task.id],
            TaskStatusUpdateEvent(
                id=task.id,
                status=task.status,
                final=(task.status.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED])
            )
        )

async def _send_push_notification(self, config, event) -> None:
    """Send a push notification to the specified endpoint."""
    # Implement push notification logic here
    # This typically involves making an HTTP request to the specified URL
    # with the event data and any required authentication
    pass
```

## Examples

### Simple Echo Agent

Here's a complete example of a simple echo agent that responds to messages:

```python
import asyncio
import logging
from agentic_kernel.communication.a2a.simple_server import create_simple_server
from agentic_kernel.communication.a2a.task import InMemoryTaskManager
from agentic_kernel.communication.a2a.types import (
    Message,
    Task,
    TaskState,
    Artifact,
    TextPart
)

class EchoTaskManager(InMemoryTaskManager):
    """Task manager for the echo agent."""
    
    async def _process_task_message(self, task: Task, message: Message) -> None:
        """Process a task message by echoing it back."""
        # Update task status to WORKING
        await self.update_task_status(task.id, TaskState.WORKING)
        
        try:
            # Extract text from the message
            text = ""
            for part in message.parts:
                if hasattr(part, "text"):
                    text += part.text
            
            # Create an artifact with the echoed text
            artifact = Artifact(
                name="echo",
                parts=[
                    TextPart(
                        type="text",
                        text=f"Echo: {text}"
                    )
                ]
            )
            
            # Add the artifact to the task
            await self.add_task_artifact(task.id, artifact)
            
            # Update task status to COMPLETED
            await self.update_task_status(task.id, TaskState.COMPLETED)
        
        except Exception as e:
            # Log the error
            logging.error(f"Error processing task {task.id}: {str(e)}")
            
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

async def main():
    # Create a task manager
    task_manager = EchoTaskManager()
    
    # Create a simple A2A server
    server = create_simple_server(
        name="EchoAgent",
        description="A simple agent that echoes messages",
        version="1.0.0",
        task_manager=task_manager,
        host="localhost",
        port=8000,
        debug=True,
    )
    
    # Run the server
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

By following this guide, you can create A2A-compatible agents that can seamlessly communicate and collaborate with other
agents in the Agentic Kernel system.