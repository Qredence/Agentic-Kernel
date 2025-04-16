# AgenticKernel Usage Guide

This guide provides practical steps and examples for using AgenticKernel in your projects.

## Basic Workflow

1. **Install AgenticKernel**
2. **Define or select agents**
3. **Create tasks and assign to agents**
4. **Run the orchestrator or task manager**

## Example: Basic Agent Task Execution

```python
from agentic_kernel import Agent, TaskManager

agent = Agent()
task_manager = TaskManager()
result = task_manager.submit(agent, "Summarize this document.")
print(result)
```

## Advanced Usage

- Multi-agent collaboration
- Custom plugins
- Integrating with AgenticFleet

See [advanced.md](advanced.md) for more.
