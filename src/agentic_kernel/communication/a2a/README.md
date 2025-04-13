# A2A Protocol Implementation

This module implements the A2A (Agent2Agent) protocol, an open standard initiated by Google designed to enable
communication and interoperability between disparate AI agent systems.

## Overview

The A2A protocol is designed to allow agents built on different frameworks (e.g., LangGraph, CrewAI, Google ADK, Genkit)
or by different vendors to discover each other's capabilities, negotiate interaction modes (text, forms, files), and
collaborate on tasks.

Key features of the A2A protocol include:

- Agent discovery via Agent Cards
- Standardized task management (send, get, cancel)
- Support for different content types (text, files, structured data) via `Parts` and `Artifacts`
- Streaming updates for long-running tasks
- Mechanisms for push notifications

## Components

This implementation includes the following components:

### Core Components

- **Types (`types.py`)**: Data types for the A2A protocol, including JSON-RPC messages, tasks, artifacts, agent cards,
  etc.
- **JSON-RPC (`jsonrpc.py`)**: Implementation of the JSON-RPC 2.0 communication layer.
- **Server (`server.py`)**: Base class for A2A servers, handling HTTP requests, method registration, and streaming
  responses.
- **Client (`client.py`)**: Client for making A2A requests to servers, including support for streaming responses.
- **Task Management (`task.py`)**: Task lifecycle management, including task state, history tracking, and artifact
  management.

### Implementations

- **Simple Server (`simple_server.py`)**: A simple implementation of the A2A server that uses the task manager to handle
  tasks.
- **Examples (`examples/`)**: Example scripts demonstrating how to use the A2A protocol implementation.

## Usage

### Creating an A2A Server

```python
from agentic_kernel.communication.a2a.simple_server import create_simple_server
from agentic_kernel.communication.a2a.task import InMemoryTaskManager

# Create a task manager
task_manager = InMemoryTaskManager()

# Create a simple A2A server
server = create_simple_server(
    name="SimpleEchoAgent",
    description="A simple A2A server that echoes messages",
    version="1.0.0",
    task_manager=task_manager,
    host="localhost",
    port=8000,
    debug=True,
)

# Run the server
server.run()
```

### Using the A2A Client

```python
import asyncio
from agentic_kernel.communication.a2a.client import A2AClient
from agentic_kernel.communication.a2a.types import Message, TaskSendParams, TextPart

async def main():
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
                        text="Hello, A2A!",
                    )
                ],
            ),
        )
        task = await client.tasks_send(task_params)
        print(f"Task ID: {task.id}")
        print(f"Task status: {task.status.state}")
        
        # Get the task
        task = await client.tasks_get(task.id)
        print(f"Task status: {task.status.state}")
        
        # Send a task with streaming
        task_params = TaskSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Hello, A2A with streaming!",
                    )
                ],
            ),
        )
        
        async for event in client.tasks_send_subscribe(task_params):
            print(f"Event: {event}")
    
    finally:
        # Close the client
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Examples

See the `examples/` directory for complete examples of how to use the A2A protocol implementation.

### Running the Simple Example

To run the server:

```bash
python -m agentic_kernel.communication.a2a.examples.simple_example --mode server
```

To run the client:

```bash
python -m agentic_kernel.communication.a2a.examples.simple_example --mode client
```

## References

- [A2A Protocol Specification](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A Protocol Documentation](https://github.com/google/a2a)