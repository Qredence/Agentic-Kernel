# Agentic Kernel Core Agent Components

This directory contains the core components for building agents in the Agentic Kernel. The code has been refactored into
a modular architecture to improve maintainability, readability, and extensibility.

## Architecture

The core agent functionality is organized into the following components:

### Base Agent

[`base_agent.py`](./base_agent.py) - Contains the `BaseAgent` abstract class that defines the core functionality and
interface for all agents in the system.

- `BaseAgent`: Abstract base class with core agent functionality
- `TaskCapability`: Type definition for agent task capabilities
- `AgentCapabilities`: Type definition for agent capabilities

### Mixins

The functionality from the original monolithic `BaseAgent` has been split into focused mixins:

- [`message_handling.py`](./message_handling.py) - Contains the `MessageHandlingMixin` for handling different types of
  messages between agents
- [`consensus.py`](./consensus.py) - Contains the `ConsensusMixin` for building consensus among agents
- [`feedback.py`](./feedback.py) - Contains the `FeedbackMixin` for handling feedback and performance metrics

### Enhanced Agent

[`enhanced_agent.py`](./enhanced_agent.py) - Combines all the mixins into a comprehensive agent implementation:

- `EnhancedAgent`: Abstract class that combines `BaseAgent` with all mixins
- `SimpleEnhancedAgent`: Concrete implementation with basic task execution and query handling

## Usage

### Basic Usage

For most use cases, you can extend `SimpleEnhancedAgent` or `EnhancedAgent`:

```python
from agentic_kernel.agents import SimpleEnhancedAgent


class MyAgent(SimpleEnhancedAgent):
  def _execute_task(self, task):
    # Custom task execution logic
    return {"status": "completed", "result": "Task executed"}

  def handle_query(self, query, context):
    # Custom query handling logic
    return {"response": f"Processed query: {query}"}
```

### Advanced Usage

For more specialized needs, you can use the individual components:

```python
from agentic_kernel.agents import BaseAgent, MessageHandlingMixin, ConsensusMixin


class MySpecializedAgent(BaseAgent, MessageHandlingMixin):
  # Only include the mixins you need

  def _execute_task(self, task):
    # Custom task execution logic
    return {"status": "completed", "result": "Task executed"}

  def handle_query(self, query, context):
    # Custom query handling logic
    return {"response": f"Processed query: {query}"}
```

## Benefits of the New Architecture

1. **Modularity**: Each component has a single responsibility, making the code easier to understand and maintain.
2. **Extensibility**: You can easily add new functionality by creating new mixins or extending existing ones.
3. **Flexibility**: You can choose which components to use based on your specific needs.
4. **Testability**: Smaller, focused components are easier to test in isolation.
5. **Readability**: Code is organized into logical units with clear responsibilities.

## Backward Compatibility

The new architecture maintains backward compatibility with existing code:

- `BaseAgent` is still available from `agentic_kernel.agents`
- All existing agent implementations continue to work as before
- New code can take advantage of the modular architecture