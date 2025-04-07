# Orchestrator Agent Developer Guide

This guide provides detailed information for developers who want to work with, extend, or customize the Orchestrator Agent in the Agentic Kernel framework.

## Overview

The Orchestrator Agent is the central coordination component in the Agentic Kernel architecture. It's responsible for planning task execution, delegating to specialized agents, monitoring progress, and handling errors. The implementation uses a nested loop architecture to separate planning from execution concerns.

## Core Implementation

The Orchestrator is implemented in `src/agentic_kernel/orchestrator.py` as the `OrchestratorAgent` class.

### Key Dependencies

The Orchestrator depends on several core components:

- **TaskLedger**: Stores task information and results (`src/agentic_kernel/ledgers.py`)
- **ProgressLedger**: Tracks workflow execution progress (`src/agentic_kernel/ledgers.py`)
- **BaseAgent**: Interface implemented by all agents (`src/agentic_kernel/agents/base.py`)
- **Task** and **WorkflowStep**: Data structures representing units of work (`src/agentic_kernel/types.py`)

### Configuration

The Orchestrator's behavior can be customized through several configuration parameters:

```python
self.max_planning_attempts = 3        # Maximum number of planning attempts
self.max_inner_loop_iterations = 10   # Maximum iterations in the inner execution loop
self.reflection_threshold = 0.7       # Progress threshold before reflection/replanning
```

## Key Methods

### Initialization

```python
def __init__(self, config: AgentConfig, task_ledger: TaskLedger, progress_ledger: ProgressLedger):
    """Initialize the orchestrator with configuration and ledgers."""
```

### Agent Registration

```python
def register_agent(self, agent: BaseAgent):
    """Register an agent with the orchestrator."""
```

### Workflow Execution

```python
async def execute_workflow(self, workflow: List[WorkflowStep]) -> Dict[str, Any]:
    """Execute a workflow composed of multiple steps."""
```

### Dynamic Workflow Creation

```python
async def create_dynamic_workflow(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[WorkflowStep]:
    """Create a dynamic workflow for a given goal."""
```

### Replanning

```python
async def _replan_workflow(self, workflow_id: str, current_workflow: List[WorkflowStep], 
                          completed_steps: List[str], failed_steps: List[str]) -> List[WorkflowStep]:
    """Create a revised plan based on current progress."""
```

## Nested Loop Architecture

The Orchestrator uses a nested loop architecture to separate concerns:

### Outer Loop (Planning)

The outer loop manages the task ledger and handles planning/replanning:

```python
# OUTER LOOP: Manages the task ledger and planning
while planning_attempts < self.max_planning_attempts:
    planning_attempts += 1
    
    if planning_attempts > 1:
        # Re-plan the workflow
        workflow = await self._replan_workflow(...)
        # Reset states for all agents
        for agent in self.agents.values():
            await self._reset_agent_state(agent)
    
    # INNER LOOP execution...
    
    # Check if no more replanning is needed
    if not await self._should_replan(...):
        break
```

### Inner Loop (Execution)

The inner loop manages the progress ledger and handles step execution:

```python
# INNER LOOP: Manages the progress ledger and step execution
while inner_loop_iterations < self.max_inner_loop_iterations:
    inner_loop_iterations += 1
    
    # Check if workflow is complete
    if len(completed_steps) + len(failed_steps) >= len(workflow):
        break
    
    # Check for looping behavior
    if inner_loop_iterations > len(workflow) * 2:
        break
    
    # Get steps ready for execution
    ready_steps = self.progress_ledger.get_ready_steps(workflow_id)
    
    # Execute ready steps...
    
    # Check for progress
    progress = self._calculate_progress(...)
    if progress < self.reflection_threshold and inner_loop_iterations > 3:
        break  # Break to outer loop for replanning
```

## Error Recovery

The Orchestrator implements several error recovery mechanisms:

1. **Step Retries**: Individual steps can be retried multiple times:

```python
retries = 0
while retries <= task.max_retries:
    try:
        # Execute task
        result = await agent.execute(task)
        return {"status": "success", ...}
    except Exception as e:
        retries += 1
        if retries > task.max_retries:
            return {"status": "failed", ...}
        await asyncio.sleep(1 * retries)  # Exponential backoff
```

2. **Replanning**: Determining when to replan:

```python
async def _should_replan(self, workflow, completed_steps, failed_steps) -> bool:
    # If all steps are either completed or failed, no need to replan
    if len(completed_steps) + len(failed_steps) >= len(workflow):
        return False
        
    # If there are no failed steps, no need to replan
    if not failed_steps:
        return False
        
    # If a critical step has failed, we should replan
    for step_name in failed_steps:
        step = next((s for s in workflow if s.task.name == step_name), None)
        if step and step.task.parameters.get("critical", False):
            return True
            
    # If more than 25% of steps have failed, we should replan
    if len(failed_steps) / len(workflow) > 0.25:
        return True
        
    return False
```

## Progress Monitoring

The Orchestrator monitors progress using a weighted calculation:

```python
def _calculate_progress(self, workflow, completed_steps, failed_steps) -> float:
    if not workflow:
        return 1.0
        
    # Weight completed steps fully, failed steps partially
    weighted_completed = len(completed_steps) + (len(failed_steps) * 0.25)
    return weighted_completed / len(workflow)
```

## Extension Points

### Creating Custom Agent Types

To extend the system with new agent types:

1. Create a new agent class that inherits from `BaseAgent`
2. Implement the required methods (`execute`, etc.)
3. Register the agent with the Orchestrator:

```python
orchestrator.register_agent(my_custom_agent)
```

### Customizing Workflow Creation

To customize how workflows are created:

1. Override the `create_dynamic_workflow` method in a subclass
2. Implement custom logic for breaking down goals into tasks

```python
class MyOrchestrator(OrchestratorAgent):
    async def create_dynamic_workflow(self, goal, context=None):
        # Custom workflow creation logic
        # ...
        return workflow
```

### Adding Custom Metrics

To add custom metrics to the workflow execution:

1. Extend the metrics dictionary in `execute_workflow`
2. Add custom metrics collection in your agent's `execute` method
3. Return metrics as part of the result dictionary

## Best Practices

1. **Agent State Management**: Ensure agents properly implement reset to clear state
2. **Task Parameters**: Include sufficient context in task parameters
3. **Error Handling**: Always handle exceptions in agent execution
4. **Progress Reporting**: Update task status promptly
5. **Task Dependencies**: Be careful with circular dependencies
6. **Timeout Handling**: Set appropriate timeouts for long-running tasks
7. **Logging**: Use the logger for debugging and tracing execution

## Common Pitfalls

1. **Circular Dependencies**: Creating circular dependencies in workflow steps
2. **Missing Agents**: Referencing agent types that aren't registered
3. **Insufficient Context**: Not providing enough context in task parameters
4. **State Leakage**: Not properly resetting agent state between plans
5. **Timeout Management**: Not handling long-running tasks properly

## Examples

### Basic Usage

```python
# Initialize the orchestrator
orchestrator = OrchestratorAgent(config, task_ledger, progress_ledger)

# Register agents
orchestrator.register_agent(chat_agent)
orchestrator.register_agent(web_surfer_agent)
orchestrator.register_agent(file_surfer_agent)

# Create a dynamic workflow
workflow = await orchestrator.create_dynamic_workflow("Research quantum computing")

# Execute the workflow
result = await orchestrator.execute_workflow(workflow)
```

### Custom Workflow

```python
# Create a custom workflow
initial_task = Task(
    id="task_1",
    name="web_search",
    description="Search for quantum computing basics",
    agent_type="web_surfer",
    parameters={"query": "quantum computing basics"},
    status="pending",
    max_retries=3,
    created_at=datetime.now()
)

second_task = Task(
    id="task_2",
    name="summarize_results",
    description="Summarize the search results",
    agent_type="chat",
    parameters={},
    status="pending",
    max_retries=2,
    created_at=datetime.now()
)

workflow = [
    WorkflowStep(task=initial_task, dependencies=[]),
    WorkflowStep(task=second_task, dependencies=["web_search"])
]

# Execute the workflow
result = await orchestrator.execute_workflow(workflow)
```

## Testing

When testing Orchestrator behavior:

1. Create mock agents that implement the `BaseAgent` interface
2. Use in-memory ledgers for testing
3. Create simple workflows with predictable behavior
4. Test error recovery by creating agents that fail in specific ways

Example:

```python
# Create a mock agent that always succeeds
class MockSuccessAgent(BaseAgent):
    async def execute(self, task):
        return {"status": "success", "result": "Mock result"}

# Create a mock agent that always fails
class MockFailureAgent(BaseAgent):
    async def execute(self, task):
        raise ValueError("Mock failure")

# Test the Orchestrator's error recovery
orchestrator.register_agent(MockSuccessAgent(AgentConfig(...)))
orchestrator.register_agent(MockFailureAgent(AgentConfig(...)))

# Create a workflow with steps using both agents
workflow = [...]

# Execute and verify replanning behavior
result = await orchestrator.execute_workflow(workflow)
assert result["replanned"] == True
``` 