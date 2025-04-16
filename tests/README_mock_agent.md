# Mock Agent for Testing Agent Communication Patterns

This directory contains a mock agent implementation for testing agent communication patterns in the Agentic Kernel
system. The mock agent can be configured to respond to different types of messages in specific ways, allowing for
controlled testing of agent interactions.

## Overview

The `MockAgent` class extends the `BaseAgent` class and provides additional functionality for testing:

- Recording and retrieving messages sent and received by the agent
- Setting custom response handlers for different message types
- Simulating agent communication patterns
- Tracking message history

## Usage

### Basic Usage

```python
from tests.mock_agent import MockAgent
from src.agentic_kernel.communication.protocol import MessageBus
from src.agentic_kernel.types import Task

# Create a message bus for agent communication
message_bus = MessageBus()
message_bus.start()

# Create a mock agent
agent = MockAgent(
    agent_id="test_agent",
    message_bus=message_bus,
    capabilities={"task_execution": True, "query_handling": True},
)

# Execute a task
task = Task(
    task_id="test_task",
    description="Test task",
    agent_id="test_agent",
    parameters={"param1": "value1"},
)
result = await agent.execute(task)

# Handle a query
query = "What is the meaning of life?"
context = {"context_key": "context_value"}
result = await agent.handle_query(query, context)

# Clean up
message_bus.stop()
```

### Testing Agent Communication

```python
# Create two mock agents for testing communication
agent1 = MockAgent(
    agent_id="agent1",
    message_bus=message_bus,
    capabilities={"task_execution": True, "query_handling": True},
)

agent2 = MockAgent(
    agent_id="agent2",
    message_bus=message_bus,
    capabilities={"task_execution": True, "query_handling": False},
)

# Agent1 sends a task request to Agent2
await agent1.request_task(
    recipient_id="agent2",
    task_description="Test task from agent1 to agent2",
    parameters={"param1": "value1"},
)

# Check that Agent2 received the task request
messages = agent2.get_received_messages(MessageType.TASK_REQUEST)
assert len(messages) == 1
assert messages[0].sender == "agent1"
assert messages[0].receiver == "agent2"
assert messages[0].content["description"] == "Test task from agent1 to agent2"
```

### Custom Response Handlers

```python
# Create a custom handler for task requests
async def custom_task_handler(message: Message):
    # Process the message in a custom way
    print(f"Received task request: {message.content['description']}")
    # Perform custom actions...

# Set the custom handler for the agent
agent.set_response_handler(MessageType.TASK_REQUEST, custom_task_handler)
```

### Message History

```python
# Clear any existing messages
agent.clear_message_history()

# Send a message
await agent.request_task(
    recipient_id="other_agent",
    task_description="Test task",
    parameters={"param1": "value1"},
)

# Check sent messages
sent_messages = agent.get_sent_messages()
assert len(sent_messages) == 1
assert sent_messages[0].message_type == MessageType.TASK_REQUEST

# Check received messages
received_messages = agent.get_received_messages()
# ...

# Clear message history
agent.clear_message_history()
```

## API Reference

### MockAgent

#### Constructor

```python
MockAgent(
    agent_id: str,
    message_bus: Optional[MessageBus] = None,
    config: Optional[AgentConfig] = None,
    capabilities: Optional[Dict[str, Any]] = None,
    response_handlers: Optional[Dict[MessageType, Callable[[Message], Awaitable[None]]]] = None,
)
```

#### Methods

- `execute(task: Task) -> Dict[str, Any]`: Execute a task
- `handle_query(query: str, context: Dict[str, Any]) -> Dict[str, Any]`: Handle a query
- `record_message(message: Message, is_sent: bool = False) -> None`: Record a message
- `get_received_messages(message_type: Optional[MessageType] = None) -> List[Message]`: Get received messages
- `get_sent_messages(message_type: Optional[MessageType] = None) -> List[Message]`: Get sent messages
- `clear_message_history() -> None`: Clear message history
- `set_response_handler(message_type: MessageType, handler: Callable[[Message], Awaitable[None]]) -> None`: Set a custom
  response handler
- `get_capabilities() -> Dict[str, Any]`: Get agent capabilities

## Examples

See `test_mock_agent.py` for examples of how to use the `MockAgent` class for testing agent communication patterns.