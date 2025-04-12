# Task Decomposition System

This module provides a system for decomposing complex tasks into smaller, more manageable subtasks. It enables agents to break down complex problems, manage dependencies between subtasks, and coordinate their execution.

## Key Components

### Task Representation

- **ComplexTask**: Extends the base `Task` class with properties and methods specific to complex tasks that can be decomposed into subtasks.
- **SubTask**: Extends the base `Task` class with additional properties specific to subtasks, such as parent task ID and dependency information.

### Decomposition Strategies

The system supports multiple strategies for decomposing tasks:

- **SequentialDecompositionStrategy**: Breaks a complex task into a sequence of subtasks that must be executed in order.
- **ParallelDecompositionStrategy**: Breaks a complex task into multiple subtasks that can be executed in parallel.
- **HierarchicalDecompositionStrategy**: Breaks a complex task into a hierarchy of subtasks, with higher-level subtasks depending on the completion of their child subtasks.
- **DomainSpecificDecompositionStrategy**: Base class for domain-specific decomposition strategies that use domain knowledge to decompose tasks.

### Task Decomposer

The `TaskDecomposer` class provides the core functionality for decomposing complex tasks into subtasks, managing dependencies between subtasks, and coordinating their execution.

## Usage Examples

### Creating and Decomposing a Complex Task

```python
from agentic_kernel.task_decomposition import TaskDecomposer
from agentic_kernel.task_decomposition_strategies import SequentialDecompositionStrategy
from agentic_kernel.task_manager import TaskManager
from agentic_kernel.ledgers import TaskLedger, ProgressLedger

# Create task manager and decomposer
task_ledger = TaskLedger()
progress_ledger = ProgressLedger()
task_manager = TaskManager(task_ledger, progress_ledger)
decomposer = TaskDecomposer(task_manager)

# Register decomposition strategies
decomposer.register_strategy(SequentialDecompositionStrategy())

# Create a complex task
task = decomposer.create_complex_task(
    name="process_data",
    description="Process and analyze data",
    agent_type="data_processor",
    parameters={
        "steps": [
            {
                "description": "Load data",
                "agent_type": "data_loader",
                "parameters": {"source": "data.csv"}
            },
            {
                "description": "Clean data",
                "agent_type": "data_cleaner",
                "parameters": {"remove_nulls": True}
            },
            {
                "description": "Analyze data",
                "agent_type": "data_analyzer",
                "parameters": {"analysis_type": "regression"}
            }
        ]
    },
    decomposition_strategy="sequential"
)

# Decompose the task into subtasks
subtasks = await decomposer.decompose_task(task.id)

# Execute subtasks
while not await decomposer.execute_subtasks(task.id):
    # Check progress
    progress = decomposer.get_task_progress(task.id)
    print(f"Task progress: {progress * 100:.0f}%")
```

### Creating a Workflow from a Decomposed Task

```python
# Create a workflow from a decomposed task
workflow_steps = decomposer.create_workflow_from_task(task.id)

# The workflow can be executed by a workflow engine
for step in workflow_steps:
    print(f"Step: {step.task.name}, Dependencies: {step.dependencies}")
```

### Creating a Custom Decomposition Strategy

```python
from agentic_kernel.task_decomposition import DecompositionStrategy, ComplexTask, SubTask

class CustomDecompositionStrategy(DecompositionStrategy):
    def __init__(self):
        super().__init__(
            name="custom",
            description="Custom decomposition strategy"
        )
    
    def decompose(self, task: ComplexTask) -> List[SubTask]:
        # Custom logic for decomposing the task
        subtasks = []
        
        # Create subtasks based on task parameters
        for i, item in enumerate(task.parameters.get("items", [])):
            subtask = SubTask(
                name=f"{task.name}_item_{i+1}",
                description=f"Process item {i+1}",
                agent_type=task.agent_type,
                parameters={"item": item},
                parent_task_id=task.id,
                dependencies=[]
            )
            subtasks.append(subtask)
        
        return subtasks

# Register the custom strategy
decomposer.register_strategy(CustomDecompositionStrategy())
```

## Integration with Agent Communication

The task decomposition system integrates with the agent communication protocol to enable collaborative task decomposition and execution:

```python
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus

# Create message bus and protocol
message_bus = MessageBus()
protocol = CommunicationProtocol("agent1", message_bus)

# Create decomposer with protocol
decomposer = TaskDecomposer(task_manager, protocol)

# When a task is decomposed, the decomposer will send a task decomposition message
# to the agent type that handles the task
subtasks = await decomposer.decompose_task(task.id)
```

## Benefits of Task Decomposition

1. **Complexity Management**: Break down complex tasks into manageable pieces
2. **Parallel Execution**: Execute independent subtasks in parallel
3. **Specialized Handling**: Assign subtasks to specialized agents
4. **Progress Tracking**: Monitor progress at a granular level
5. **Dependency Management**: Handle dependencies between subtasks
6. **Failure Isolation**: Isolate failures to specific subtasks