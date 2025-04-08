# Multi-Agent Workflow Example

This example demonstrates how to create and execute complex workflows with multiple agents in the Agentic Kernel framework.

## Overview

The example includes several sample workflows that showcase different patterns of agent collaboration:

1. **Web Research and Code Generation**: Combines WebSurferAgent and CoderAgent to research a topic and generate code based on findings.
2. **File Analysis and Processing**: Uses FileSurferAgent, CoderAgent, and TerminalAgent to analyze project files and execute transformations.
3. **Data Pipeline Workflow**: Creates a data processing pipeline involving multiple agents working in sequence.
4. **Error Recovery Workflow**: Demonstrates how to handle errors and implement recovery mechanisms across agents.
5. **Conditional Execution Workflow**: Shows how to create workflows with conditional paths based on dynamic evaluation.

## Requirements

- Python 3.8+
- Agentic Kernel installed (`pip install agentic-kernel`)
- Optional: API keys for external services (OpenAI, etc.)

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure your environment variables:
   ```
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

## Usage

### Basic Usage

Run the basic workflow example:

```bash
python -m examples.multi_agent_workflow.web_research_code_generation
```

### Advanced Usage

For more complex workflow examples:

```bash
# File analysis workflow
python -m examples.multi_agent_workflow.file_analysis_processing

# Data pipeline workflow
python -m examples.multi_agent_workflow.data_pipeline

# Error recovery workflow
python -m examples.multi_agent_workflow.error_recovery

# Conditional execution workflow
python -m examples.multi_agent_workflow.conditional_execution
```

## Workflow Structure

Each workflow is defined as a list of `WorkflowStep` objects, where each step:

1. Is associated with a specific task
2. May depend on other steps
3. May include conditional execution logic
4. Can specify error handling and retry behavior

Example workflow definition:

```python
workflow = [
    WorkflowStep(
        task=Task(
            name="research_topic",
            description="Research information about Python async patterns",
            agent_type="web_surfer",
            parameters={"query": "Python asyncio best practices"}
        ),
        dependencies=[]
    ),
    WorkflowStep(
        task=Task(
            name="generate_code",
            description="Generate sample code based on research",
            agent_type="coder",
            parameters={"language": "python", "task": "Create async utility functions"}
        ),
        dependencies=["research_topic"]
    )
]
```

## Extending the Examples

You can modify these examples to create your own workflows:

1. Add new task types by creating custom `Task` objects
2. Change agent configurations in the `config.py` file
3. Modify workflow dependencies to create different execution patterns
4. Add new agent types by extending the `BaseAgent` class

## Visualizing Workflows

The examples include utilities for visualizing workflow execution:

```python
from examples.multi_agent_workflow.utils import visualize_workflow

# After executing a workflow
visualize_workflow(result)
```

This generates a visualization of the workflow execution, including task dependencies, execution times, and status. 