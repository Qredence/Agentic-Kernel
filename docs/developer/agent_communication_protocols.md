# Agent Communication Protocols

## Introduction

This document provides comprehensive documentation for the agent communication protocols used in the Agentic Kernel
system, with a focus on the A2A (Agent-to-Agent) protocol implementation.

## Table of Contents

1. [A2A Protocol Overview](#a2a-protocol-overview)
2. [Protocol Components](#protocol-components)
3. [Message Structure](#message-structure)
4. [Task Lifecycle](#task-lifecycle)
5. [Agent Capabilities and Discovery](#agent-capabilities-and-discovery)
6. [Communication Patterns](#communication-patterns)
7. [Error Handling](#error-handling)
8. [Implementation Details](#implementation-details)
9. [Examples](#examples)
10. [References](#references)

## A2A Protocol Overview

The A2A (Agent-to-Agent) protocol is an open standard initiated by Google designed to enable communication and
interoperability between disparate AI agent systems. It allows agents built on different frameworks (e.g., LangGraph,
CrewAI, Google ADK, Genkit) or by different vendors to discover each other's capabilities, negotiate interaction modes,
and collaborate on tasks.

Key features of the A2A protocol include:

- Agent discovery via Agent Cards
- Standardized task management (send, get, cancel)
- Support for different content types (text, files, structured data) via `Parts` and `Artifacts`
- Streaming updates for long-running tasks
- Mechanisms for push notifications

The protocol is built on top of JSON-RPC 2.0, which provides a lightweight, transport-agnostic RPC mechanism.

## Protocol Components

The A2A protocol implementation in Agentic Kernel consists of the following components:

### Core Components

- **Types**: Data types for the A2A protocol, including JSON-RPC messages, tasks, artifacts, agent cards, etc.
- **JSON-RPC**: Implementation of the JSON-RPC 2.0 communication layer.
- **Server**: Base class for A2A servers, handling HTTP requests, method registration, and streaming responses.
- **Client**: Client for making A2A requests to servers, including support for streaming responses.
- **Task Management**: Task lifecycle management, including task state, history tracking, and artifact management.

### Implementations

- **Simple Server**: A simple implementation of the A2A server that uses the task manager to handle tasks.
- **Examples**: Example scripts demonstrating how to use the A2A protocol implementation.

## Message Structure

The A2A protocol uses a standardized message structure for communication between agents. Messages are encoded as
JSON-RPC 2.0 requests and responses.

### JSON-RPC 2.0 Message Format

#### Request

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "method": "method-name",
    "params": {
        // Method-specific parameters
    }
}
```

#### Response

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "result": {
        // Method-specific result
    }
}
```

#### Error Response

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "error": {
        "code": -32000,
        "message": "Error message",
        "data": {
            // Additional error information
        }
    }
}
```

### A2A Message Types

The A2A protocol defines several message types for different purposes:

#### Task Assignment

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "method": "tasks/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "type": "text",
                    "text": "Task description"
                }
            ]
        }
    }
}
```

#### Task Status Update

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "result": {
        "id": "task-id",
        "status": {
            "state": "working",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    }
}
```

#### Task Artifact Update

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "result": {
        "id": "task-id",
        "artifact": {
            "name": "artifact-name",
            "parts": [
                {
                    "type": "text",
                    "text": "Artifact content"
                }
            ]
        }
    }
}
```

## Task Lifecycle

Tasks in the A2A protocol go through a defined lifecycle, represented by the `TaskState` enum:

1. **SUBMITTED**: The task has been submitted to the agent but processing has not yet begun.
2. **WORKING**: The agent is actively working on the task.
3. **INPUT_REQUIRED**: The agent requires additional input from the user to continue processing the task.
4. **COMPLETED**: The task has been successfully completed.
5. **CANCELED**: The task has been canceled by the user or the agent.
6. **FAILED**: The task has failed due to an error.
7. **UNKNOWN**: The task state is unknown.

The task lifecycle is managed by the `TaskManager` class, which provides methods for:

- Processing tasks (`process_task`)
- Getting task information (`get_task`)
- Canceling tasks (`cancel_task`)
- Subscribing to task updates (`subscribe_to_task`)
- Updating task status (`update_task_status`)
- Adding task artifacts (`add_task_artifact`)

## Agent Capabilities and Discovery

Agents in the A2A protocol advertise their capabilities through Agent Cards, which include:

- Agent name and description
- Provider information
- Version
- Capabilities (streaming, push notifications, etc.)
- Authentication requirements
- Input and output modes
- Skills

Agent Cards are retrieved using the `agent/getCard` method:

```json
{
    "jsonrpc": "2.0",
    "id": "request-id",
    "method": "agent/getCard",
    "params": {}
}
```

## Communication Patterns

The A2A protocol supports several communication patterns:

### Request-Response

The simplest pattern, where a client sends a request and the server responds with a result or error.

### Streaming

For long-running tasks, the server can stream updates to the client using the `tasks/sendSubscribe` and
`tasks/resubscribe` methods.

### Push Notifications

Agents can send push notifications to clients for asynchronous updates, using the push notification configuration
provided in the task parameters.

## Error Handling

The A2A protocol defines several error codes for different types of errors:

- **Standard JSON-RPC error codes**:
    - `-32700`: Parse error
    - `-32600`: Invalid request
    - `-32601`: Method not found
    - `-32602`: Invalid params
    - `-32603`: Internal error

- **A2A-specific error codes**:
    - `-32001`: Task not found
    - `-32002`: Task not cancelable
    - `-32003`: Push notification not supported
    - `-32004`: Unsupported operation
    - `-32005`: Content type not supported

Errors are returned in the standard JSON-RPC error format.

## Implementation Details

### Server Implementation

The A2A server is implemented as a FastAPI application that handles JSON-RPC requests and responses. The server
registers methods for the A2A protocol and delegates task processing to the `TaskManager`.

### Client Implementation

The A2A client provides methods for making requests to A2A servers, including support for streaming responses. The
client handles JSON-RPC encoding and decoding, as well as error handling.

### Task Management

The `TaskManager` class manages the lifecycle of tasks, including:

- Creating and updating tasks
- Tracking task status and history
- Managing task artifacts
- Notifying subscribers of task updates

## Examples

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

## References

- [A2A Protocol Specification](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A Protocol Documentation](https://github.com/google/a2a)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)