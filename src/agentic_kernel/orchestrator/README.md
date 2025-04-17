# Agentic Kernel Orchestrator Components

This directory contains the core orchestration components for the Agentic Kernel. The orchestrator is responsible for
managing workflows, coordinating agents, and tracking metrics.

## Component Overview

### Agent Management

- `agent_manager.py`: Manages agent registration, specialization, and selection

### Workflow Management

- `workflow_executor.py`: Executes workflows and manages their execution state
- `workflow_planner.py`: Plans and replans workflows
- `workflow_history.py`: Tracks workflow versions and execution history
- `workflow_optimizer.py`: Optimizes workflows for better performance

### Metrics and Monitoring

- `metrics_manager.py`: Collects and reports metrics about agent performance
- `agent_metrics.py`: Tracks metrics for individual agents

### Utilities

- `condition_evaluator.py`: Evaluates conditions for conditional branching in workflows
- `agent_selection.py`: Selects the most appropriate agent for a task

## Architecture

The orchestrator uses a modular architecture where each component has a specific responsibility:

1. The `OrchestratorAgent` in `core.py` is the main entry point that coordinates all components
2. It delegates specific responsibilities to specialized components:
    - Agent registration and selection to `AgentManager`
    - Workflow execution to `WorkflowExecutor`
    - Workflow planning to `WorkflowPlanner`
    - Metrics collection to `MetricsManager`

This modular design makes the code more maintainable, testable, and extensible.

## Usage

The orchestrator is typically used through the `OrchestratorAgent` class:

```python
from agentic_kernel.orchestrator.core import OrchestratorAgent
from agentic_kernel.ledgers import TaskLedger, ProgressLedger
from agentic_kernel.config import AgentConfig

# Create an orchestrator
orchestrator = OrchestratorAgent(
    config=AgentConfig(...),
    task_ledger=TaskLedger(...),
    progress_ledger=ProgressLedger(...)
)

# Register agents
orchestrator.register_agent(my_agent)

# Create and execute workflows
workflow_id = await orchestrator.create_workflow(
    name="My Workflow",
    description="A sample workflow",
    steps=[...]
)
result = await orchestrator.execute_workflow(workflow_id)
```

## Extending the Orchestrator

To extend the orchestrator with new functionality:

1. Create a new component in a separate file
2. Update the `OrchestratorAgent` class to use the new component
3. Ensure backward compatibility is maintained