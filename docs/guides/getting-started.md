# Getting Started with Agentic Kernel

This guide will help you get started with Agentic Kernel, from installation to running your first workflow.

## Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- Git (for version control)

## Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd agentic-kernel
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   uv pip install -e .
   ```

## Basic Usage

### 1. Initialize the System

```python
from agentic_kernel import AgentSystem

# Initialize the agent system
system = AgentSystem()

# Configure the system
system.configure({
    "logging_level": "INFO",
    "max_concurrent_tasks": 5
})
```

### 2. Create a Simple Workflow

```python
from agentic_kernel import Workflow, TaskAgent

# Define a simple task
@Workflow.task
def hello_world(message: str):
    return f"Hello, {message}!"

# Create a workflow
workflow = Workflow("hello-world")
workflow.add_task(hello_world, args=["World"])

# Execute the workflow
result = system.execute(workflow)
print(result)  # Output: Hello, World!
```

### 3. Working with Agents

```python
# Create a custom agent
class MyCustomAgent(TaskAgent):
    def execute(self, task):
        # Implement custom logic
        pass

# Register the agent
system.register_agent(MyCustomAgent())

# Use the agent in a workflow
workflow.assign_agent("my-custom-agent")
```

## Next Steps

- Explore the [Examples](../examples/) directory for more complex use cases
- Read the [Architecture Overview](../architecture/system-overview.md)
- Learn about [Security Best Practices](../guides/security.md)
- Check out the [API Reference](../api/README.md)

## Troubleshooting

Common issues and their solutions:

1. **Installation Problems**
   - Ensure Python version compatibility
   - Check for system dependencies
   - Verify virtual environment activation

2. **Agent Registration Issues**
   - Confirm agent interface implementation
   - Check for configuration errors
   - Verify agent ID uniqueness

3. **Workflow Execution Errors**
   - Review task dependencies
   - Check error logs
   - Verify resource availability

## Getting Help

- Check the [FAQ](../guides/faq.md)
- Review existing [Issues](https://github.com/[repository]/issues)
- Join our community [Discord/Slack]
- Contact support at [support-email] 