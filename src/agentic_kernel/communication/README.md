# Agent Communication Module

This module provides the communication infrastructure for agents in the Agentic-Kernel system, enabling standardized message passing, routing, and handling between agents.

## Key Components

### Protocol

The `protocol.py` file implements the core communication protocol used between agents, providing:

- Message routing
- Asynchronous communication
- Message validation
- Error handling
- Delivery guarantees

### Message Types

The `message.py` file defines standardized message formats for agent communication, including:

- Task requests and responses
- Queries and responses
- Status updates
- Error notifications
- A2A-specific message types (capability requests, consensus, etc.)

### Collaborative Protocol

The `collaborative_protocol.py` file extends the base protocol with methods for collaborative memory operations, allowing agents to:

- Create and manage shared workspaces
- Store and retrieve memories
- Update and lock memories
- Comment on memories

### Capability Registry

The `capability_registry.py` file implements agent capability advertisement and discovery mechanisms, enabling:

- Agent capability registration
- Capability discovery and querying
- Agent registry for tracking available agents
- Capability matching and filtering

## Usage Examples

### Basic Message Sending

```python
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus

# Create a message bus
message_bus = MessageBus()
await message_bus.start()

# Create protocols for two agents
agent1_protocol = CommunicationProtocol("agent1", message_bus)
agent2_protocol = CommunicationProtocol("agent2", message_bus)

# Register a message handler for agent2
async def handle_message(message):
    print(f"Agent2 received: {message.content}")

agent2_protocol.register_handler(MessageType.QUERY, handle_message)

# Send a message from agent1 to agent2
await agent1_protocol.query_agent(
    recipient="agent2",
    query="What is the weather today?",
    context={"location": "San Francisco"}
)
```

### Capability Advertisement and Discovery

```python
from agentic_kernel.communication.capability_registry import (
    AgentCapability,
    CapabilityRegistry,
)
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus

# Create a message bus and protocols
message_bus = MessageBus()
await message_bus.start()
agent1_protocol = CommunicationProtocol("agent1", message_bus)
agent2_protocol = CommunicationProtocol("agent2", message_bus)

# Create a capability registry
registry = CapabilityRegistry(protocol=agent1_protocol)

# Define a capability
reasoning_capability = AgentCapability(
    name="reasoning",
    description="Logical reasoning and problem solving",
    capability_type="reasoning",
    performance_metrics={"accuracy": 0.95},
)

# Register agent2 with the capability
await registry.register_agent(
    agent_id="agent2",
    agent_type="assistant",
    capabilities=[reasoning_capability],
    status="active",
)

# Broadcast agent2's capabilities
await registry.broadcast_agent_discovery(
    agent_id="agent2",
    agent_type="assistant",
    capabilities=["reasoning"],
    status="active",
)

# Agent1 can request capabilities from agent2
await registry.request_agent_capabilities(
    recipient="agent2",
    capability_types=["reasoning"],
    detail_level="detailed",
)
```

### Collaborative Memory Operations

```python
from agentic_kernel.communication.collaborative_protocol import CollaborativeProtocol
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus

# Create a message bus and protocols
message_bus = MessageBus()
await message_bus.start()
agent1_protocol = CommunicationProtocol("agent1", message_bus)
agent2_protocol = CommunicationProtocol("agent2", message_bus)

# Create collaborative protocols
agent1_collab = CollaborativeProtocol(agent1_protocol)
agent2_collab = CollaborativeProtocol(agent2_protocol)

# Create a workspace
workspace_id = "workspace-123"
await agent1_collab.create_workspace(
    recipient="agent2",
    name="Project Workspace",
    description="A workspace for our project",
    tags=["project", "collaboration"],
)

# Store a memory in the workspace
await agent1_collab.store_memory(
    recipient="agent2",
    workspace_id=workspace_id,
    content="Important project insight",
    tags=["insight"],
    importance=0.8,
)

# Retrieve a memory
memory_id = "memory-456"
await agent2_collab.retrieve_memory(
    recipient="agent1",
    workspace_id=workspace_id,
    memory_id=memory_id,
)
```