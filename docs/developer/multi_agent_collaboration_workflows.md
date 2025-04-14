# Multi-Agent Collaboration Workflows

## Introduction

This document provides tutorials and examples for implementing multi-agent collaboration workflows in the Agentic Kernel
system. These workflows enable multiple specialized agents to work together to solve complex tasks that would be
difficult for a single agent to handle.

## Table of Contents

1. [Understanding Multi-Agent Collaboration](#understanding-multi-agent-collaboration)
2. [Prerequisites](#prerequisites)
3. [Basic Collaboration Patterns](#basic-collaboration-patterns)
4. [Tutorial: Implementing a Sequential Workflow](#tutorial-implementing-a-sequential-workflow)
5. [Tutorial: Implementing a Parallel Workflow](#tutorial-implementing-a-parallel-workflow)
6. [Tutorial: Implementing a Dynamic Workflow](#tutorial-implementing-a-dynamic-workflow)
7. [Advanced Collaboration Techniques](#advanced-collaboration-techniques)
8. [Debugging and Troubleshooting](#debugging-and-troubleshooting)
9. [Best Practices](#best-practices)
10. [Examples](#examples)

## Understanding Multi-Agent Collaboration

Multi-agent collaboration in the Agentic Kernel system involves multiple specialized agents working together to
accomplish a complex task. Each agent has specific capabilities and responsibilities, and they communicate with each
other using the A2A protocol.

Key concepts in multi-agent collaboration:

1. **Orchestration**: Coordinating the activities of multiple agents
2. **Task Decomposition**: Breaking down complex tasks into smaller subtasks
3. **Information Sharing**: Enabling agents to share information and context
4. **Dependency Management**: Managing dependencies between tasks
5. **Error Handling**: Handling errors and failures in a distributed system

## Prerequisites

Before implementing multi-agent collaboration workflows, you should have:

1. A basic understanding of the A2A protocol (see [Agent Communication Protocols](agent_communication_protocols.md))
2. Familiarity with creating A2A-compatible agents (
   see [Creating A2A-Compatible Agents](creating_a2a_compatible_agents.md))
3. Understanding of agent interaction patterns (see [Agent Interaction Patterns](agent_interaction_patterns.md))
4. Python 3.9 or later
5. The Agentic Kernel package installed

## Basic Collaboration Patterns

### Orchestrator Pattern

In this pattern, a central orchestrator agent coordinates the activities of specialized agents:

```
Orchestrator
    |
    ├── Agent A (specialized for task A)
    ├── Agent B (specialized for task B)
    └── Agent C (specialized for task C)
```

### Peer-to-Peer Pattern

In this pattern, agents communicate directly with each other without a central orchestrator:

```
Agent A ⟷ Agent B
   ↕        ↕
Agent C ⟷ Agent D
```

### Hybrid Pattern

In this pattern, a central orchestrator coordinates high-level tasks, but agents can communicate directly for specific
interactions:

```
Orchestrator
    |
    ├── Agent A ⟷ Agent B
    └── Agent C ⟷ Agent D
```

## Tutorial: Implementing a Sequential Workflow

In this tutorial, we'll implement a sequential workflow where multiple agents process a task in sequence, with each
agent building on the results of the previous agent.

### Step 1: Define the Workflow

First, define the workflow as a sequence of steps, each assigned to a specific agent:

```python
from agentic_kernel.workflow.definition import WorkflowDefinition, WorkflowStep

# Define the workflow
workflow = WorkflowDefinition(
    name="Sequential Document Processing",
    description="Process a document through multiple agents in sequence",
    steps=[
        WorkflowStep(
            name="extract_text",
            description="Extract text from a document",
            agent_type="file_surfer",
            parameters={"file_path": "document.pdf"}
        ),
        WorkflowStep(
            name="analyze_content",
            description="Analyze the content of the document",
            agent_type="coder",
            parameters={},
            dependencies=["extract_text"]
        ),
        WorkflowStep(
            name="generate_summary",
            description="Generate a summary of the document",
            agent_type="writer",
            parameters={},
            dependencies=["analyze_content"]
        )
    ]
)
```

### Step 2: Create the Agents

Create the specialized agents that will participate in the workflow:

```python
from agentic_kernel.agents.file_surfer import FileSurferAgent
from agentic_kernel.agents.coder import CoderAgent
from agentic_kernel.agents.writer import WriterAgent

# Create the agents
file_surfer = FileSurferAgent()
coder = CoderAgent()
writer = WriterAgent()

# Register the agents with the agent registry
agent_registry = AgentRegistry()
agent_registry.register("file_surfer", file_surfer)
agent_registry.register("coder", coder)
agent_registry.register("writer", writer)
```

### Step 3: Create the Workflow Manager

Create a workflow manager to execute the workflow:

```python
from agentic_kernel.workflow.manager import WorkflowManager

# Create the workflow manager
workflow_manager = WorkflowManager(agent_registry)
```

### Step 4: Execute the Workflow

Execute the workflow and handle the results:

```python
import asyncio

async def run_workflow():
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow)
    
    # Handle the results
    if result.success:
        print("Workflow completed successfully!")
        print(f"Summary: {result.outputs['generate_summary']}")
    else:
        print(f"Workflow failed: {result.error}")

# Run the workflow
asyncio.run(run_workflow())
```

### Step 5: Handle Task Dependencies

The workflow manager automatically handles task dependencies, ensuring that each step is executed only when its
dependencies are satisfied. The results of each step are passed to the next step as inputs.

For example, the `analyze_content` step depends on the `extract_text` step, so it will only be executed after
`extract_text` is completed, and it will receive the output of `extract_text` as input.

## Tutorial: Implementing a Parallel Workflow

In this tutorial, we'll implement a parallel workflow where multiple agents process tasks simultaneously.

### Step 1: Define the Workflow

Define a workflow with parallel steps:

```python
from agentic_kernel.workflow.definition import WorkflowDefinition, WorkflowStep

# Define the workflow
workflow = WorkflowDefinition(
    name="Parallel Data Processing",
    description="Process multiple data sources in parallel",
    steps=[
        WorkflowStep(
            name="fetch_data_a",
            description="Fetch data from source A",
            agent_type="web_surfer",
            parameters={"url": "https://example.com/data_a"}
        ),
        WorkflowStep(
            name="fetch_data_b",
            description="Fetch data from source B",
            agent_type="web_surfer",
            parameters={"url": "https://example.com/data_b"}
        ),
        WorkflowStep(
            name="fetch_data_c",
            description="Fetch data from source C",
            agent_type="web_surfer",
            parameters={"url": "https://example.com/data_c"}
        ),
        WorkflowStep(
            name="combine_data",
            description="Combine data from all sources",
            agent_type="data_processor",
            parameters={},
            dependencies=["fetch_data_a", "fetch_data_b", "fetch_data_c"]
        )
    ]
)
```

### Step 2: Create the Agents

Create the specialized agents:

```python
from agentic_kernel.agents.web_surfer import WebSurferAgent
from agentic_kernel.agents.data_processor import DataProcessorAgent

# Create the agents
web_surfer = WebSurferAgent()
data_processor = DataProcessorAgent()

# Register the agents with the agent registry
agent_registry = AgentRegistry()
agent_registry.register("web_surfer", web_surfer)
agent_registry.register("data_processor", data_processor)
```

### Step 3: Execute the Workflow

Execute the workflow:

```python
import asyncio

async def run_workflow():
    # Create the workflow manager
    workflow_manager = WorkflowManager(agent_registry)
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow)
    
    # Handle the results
    if result.success:
        print("Workflow completed successfully!")
        print(f"Combined data: {result.outputs['combine_data']}")
    else:
        print(f"Workflow failed: {result.error}")

# Run the workflow
asyncio.run(run_workflow())
```

### Step 4: Monitor Parallel Execution

The workflow manager executes the independent steps (`fetch_data_a`, `fetch_data_b`, `fetch_data_c`) in parallel, and
then executes the `combine_data` step once all its dependencies are satisfied.

You can monitor the progress of each step:

```python
async def run_workflow_with_monitoring():
    # Create the workflow manager
    workflow_manager = WorkflowManager(agent_registry)
    
    # Execute the workflow with progress monitoring
    async for progress in workflow_manager.execute_workflow_with_progress(workflow):
        print(f"Step: {progress.step_name}, Status: {progress.status}, Progress: {progress.progress}%")
    
    # Get the final result
    result = await workflow_manager.get_workflow_result(workflow.id)
    
    # Handle the results
    if result.success:
        print("Workflow completed successfully!")
        print(f"Combined data: {result.outputs['combine_data']}")
    else:
        print(f"Workflow failed: {result.error}")
```

## Tutorial: Implementing a Dynamic Workflow

In this tutorial, we'll implement a dynamic workflow where the workflow structure is determined at runtime based on the
results of previous steps.

### Step 1: Define the Initial Workflow

Define an initial workflow with a decision step:

```python
from agentic_kernel.workflow.definition import WorkflowDefinition, WorkflowStep

# Define the initial workflow
workflow = WorkflowDefinition(
    name="Dynamic Document Processing",
    description="Process a document with dynamic steps based on content",
    steps=[
        WorkflowStep(
            name="analyze_document",
            description="Analyze the document to determine processing steps",
            agent_type="analyzer",
            parameters={"file_path": "document.pdf"}
        ),
        WorkflowStep(
            name="decide_workflow",
            description="Decide the next steps based on document analysis",
            agent_type="decision_maker",
            parameters={},
            dependencies=["analyze_document"]
        )
    ]
)
```

### Step 2: Create a Dynamic Workflow Manager

Create a custom workflow manager that can modify the workflow at runtime:

```python
from agentic_kernel.workflow.manager import WorkflowManager

class DynamicWorkflowManager(WorkflowManager):
    """A workflow manager that can modify workflows at runtime."""
    
    async def execute_workflow(self, workflow):
        """Execute a workflow with dynamic modification."""
        # Execute the initial steps
        initial_result = await super().execute_partial_workflow(
            workflow, 
            steps=["analyze_document", "decide_workflow"]
        )
        
        if not initial_result.success:
            return initial_result
        
        # Get the decision result
        decision = initial_result.outputs["decide_workflow"]
        
        # Modify the workflow based on the decision
        modified_workflow = self._modify_workflow(workflow, decision)
        
        # Execute the modified workflow, skipping the already executed steps
        final_result = await super().execute_workflow(
            modified_workflow,
            skip_steps=["analyze_document", "decide_workflow"]
        )
        
        # Combine the results
        combined_result = WorkflowResult(
            workflow_id=workflow.id,
            success=final_result.success,
            outputs={**initial_result.outputs, **final_result.outputs},
            error=final_result.error
        )
        
        return combined_result
    
    def _modify_workflow(self, workflow, decision):
        """Modify the workflow based on the decision."""
        # Create a copy of the workflow
        modified_workflow = WorkflowDefinition(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=workflow.steps.copy()
        )
        
        # Add new steps based on the decision
        if decision["document_type"] == "text":
            modified_workflow.steps.append(
                WorkflowStep(
                    name="process_text",
                    description="Process text document",
                    agent_type="text_processor",
                    parameters={},
                    dependencies=["decide_workflow"]
                )
            )
        elif decision["document_type"] == "image":
            modified_workflow.steps.append(
                WorkflowStep(
                    name="process_image",
                    description="Process image document",
                    agent_type="image_processor",
                    parameters={},
                    dependencies=["decide_workflow"]
                )
            )
        elif decision["document_type"] == "code":
            modified_workflow.steps.append(
                WorkflowStep(
                    name="process_code",
                    description="Process code document",
                    agent_type="code_processor",
                    parameters={},
                    dependencies=["decide_workflow"]
                )
            )
        
        # Add a final summary step
        modified_workflow.steps.append(
            WorkflowStep(
                name="generate_summary",
                description="Generate a summary of the processed document",
                agent_type="summarizer",
                parameters={},
                dependencies=[step.name for step in modified_workflow.steps if step.name != "generate_summary"]
            )
        )
        
        return modified_workflow
```

### Step 3: Create the Agents

Create the specialized agents:

```python
from agentic_kernel.agents.analyzer import AnalyzerAgent
from agentic_kernel.agents.decision_maker import DecisionMakerAgent
from agentic_kernel.agents.text_processor import TextProcessorAgent
from agentic_kernel.agents.image_processor import ImageProcessorAgent
from agentic_kernel.agents.code_processor import CodeProcessorAgent
from agentic_kernel.agents.summarizer import SummarizerAgent

# Create the agents
analyzer = AnalyzerAgent()
decision_maker = DecisionMakerAgent()
text_processor = TextProcessorAgent()
image_processor = ImageProcessorAgent()
code_processor = CodeProcessorAgent()
summarizer = SummarizerAgent()

# Register the agents with the agent registry
agent_registry = AgentRegistry()
agent_registry.register("analyzer", analyzer)
agent_registry.register("decision_maker", decision_maker)
agent_registry.register("text_processor", text_processor)
agent_registry.register("image_processor", image_processor)
agent_registry.register("code_processor", code_processor)
agent_registry.register("summarizer", summarizer)
```

### Step 4: Execute the Dynamic Workflow

Execute the dynamic workflow:

```python
import asyncio

async def run_dynamic_workflow():
    # Create the dynamic workflow manager
    workflow_manager = DynamicWorkflowManager(agent_registry)
    
    # Execute the workflow
    result = await workflow_manager.execute_workflow(workflow)
    
    # Handle the results
    if result.success:
        print("Workflow completed successfully!")
        print(f"Summary: {result.outputs['generate_summary']}")
    else:
        print(f"Workflow failed: {result.error}")

# Run the workflow
asyncio.run(run_dynamic_workflow())
```

## Advanced Collaboration Techniques

### Context Sharing

Agents can share context with each other to improve collaboration:

```python
# Agent A: Store information in shared context
shared_context = {"key_insight": "Important information discovered by Agent A"}
await context_manager.update_context(task_id, shared_context)

# Agent B: Retrieve information from shared context
context = await context_manager.get_context(task_id)
key_insight = context.get("key_insight")
```

### Artifact Sharing

Agents can share artifacts (files, data, etc.) with each other:

```python
# Agent A: Create and share an artifact
artifact = Artifact(
    name="analysis_result",
    parts=[
        TextPart(
            type="text",
            text="Analysis result from Agent A"
        )
    ]
)
await task_manager.add_task_artifact(task_id, artifact)

# Agent B: Retrieve and use the artifact
task = await task_manager.get_task(task_id)
for artifact in task.artifacts:
    if artifact.name == "analysis_result":
        for part in artifact.parts:
            if hasattr(part, "text"):
                analysis_result = part.text
```

### Dynamic Agent Selection

Select agents dynamically based on task requirements:

```python
def select_agent_for_task(task_description):
    """Select the most appropriate agent for a task."""
    if "code" in task_description.lower():
        return "coder"
    elif "web" in task_description.lower():
        return "web_surfer"
    elif "file" in task_description.lower():
        return "file_surfer"
    else:
        return "general_purpose"
```

## Debugging and Troubleshooting

### Logging

Use logging to track the execution of multi-agent workflows:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Log workflow execution
logging.info(f"Starting workflow: {workflow.name}")
for step in workflow.steps:
    logging.info(f"Executing step: {step.name}")
    # Execute step
    logging.info(f"Step {step.name} completed")
```

### Visualization

Visualize the workflow execution:

```python
from agentic_kernel.visualization.workflow import visualize_workflow

# Visualize the workflow
visualize_workflow(workflow, result)
```

### Error Handling

Implement robust error handling for multi-agent workflows:

```python
try:
    result = await workflow_manager.execute_workflow(workflow)
except Exception as e:
    logging.error(f"Workflow execution failed: {str(e)}")
    # Implement recovery strategy
```

## Best Practices

1. **Clearly Define Agent Responsibilities**: Each agent should have well-defined responsibilities and capabilities.
2. **Minimize Inter-Agent Dependencies**: Reduce tight coupling between agents to improve flexibility and resilience.
3. **Implement Robust Error Handling**: Handle errors gracefully at both the agent and workflow levels.
4. **Use Standardized Communication Protocols**: Use the A2A protocol for all inter-agent communication.
5. **Monitor Workflow Execution**: Implement monitoring and logging to track workflow progress and diagnose issues.
6. **Test Workflows Thoroughly**: Test workflows with various inputs and edge cases to ensure reliability.
7. **Document Agent Capabilities**: Document the capabilities and requirements of each agent to facilitate
   collaboration.
8. **Optimize Resource Usage**: Manage resources efficiently, especially for parallel workflows.
9. **Implement Timeouts and Retries**: Use timeouts and retries to handle transient failures.
10. **Provide Clear User Feedback**: Keep users informed about workflow progress and results.

## Examples

### Example 1: Code Generation and Testing Workflow

This example demonstrates a workflow for generating and testing code:

```python
from agentic_kernel.workflow.definition import WorkflowDefinition, WorkflowStep

# Define the workflow
code_workflow = WorkflowDefinition(
    name="Code Generation and Testing",
    description="Generate and test code based on requirements",
    steps=[
        WorkflowStep(
            name="parse_requirements",
            description="Parse the requirements document",
            agent_type="file_surfer",
            parameters={"file_path": "requirements.txt"}
        ),
        WorkflowStep(
            name="generate_code",
            description="Generate code based on requirements",
            agent_type="coder",
            parameters={},
            dependencies=["parse_requirements"]
        ),
        WorkflowStep(
            name="write_tests",
            description="Write tests for the generated code",
            agent_type="test_writer",
            parameters={},
            dependencies=["generate_code"]
        ),
        WorkflowStep(
            name="run_tests",
            description="Run the tests on the generated code",
            agent_type="terminal",
            parameters={},
            dependencies=["generate_code", "write_tests"]
        ),
        WorkflowStep(
            name="generate_documentation",
            description="Generate documentation for the code",
            agent_type="documentation_writer",
            parameters={},
            dependencies=["generate_code"]
        )
    ]
)
```

### Example 2: Data Analysis Workflow

This example demonstrates a workflow for analyzing data from multiple sources:

```python
from agentic_kernel.workflow.definition import WorkflowDefinition, WorkflowStep

# Define the workflow
data_workflow = WorkflowDefinition(
    name="Data Analysis",
    description="Analyze data from multiple sources",
    steps=[
        WorkflowStep(
            name="fetch_data_a",
            description="Fetch data from source A",
            agent_type="web_surfer",
            parameters={"url": "https://example.com/data_a"}
        ),
        WorkflowStep(
            name="fetch_data_b",
            description="Fetch data from source B",
            agent_type="web_surfer",
            parameters={"url": "https://example.com/data_b"}
        ),
        WorkflowStep(
            name="preprocess_data",
            description="Preprocess the fetched data",
            agent_type="data_processor",
            parameters={},
            dependencies=["fetch_data_a", "fetch_data_b"]
        ),
        WorkflowStep(
            name="analyze_data",
            description="Analyze the preprocessed data",
            agent_type="data_analyst",
            parameters={},
            dependencies=["preprocess_data"]
        ),
        WorkflowStep(
            name="visualize_results",
            description="Create visualizations of the analysis results",
            agent_type="visualization_expert",
            parameters={},
            dependencies=["analyze_data"]
        ),
        WorkflowStep(
            name="generate_report",
            description="Generate a report of the analysis",
            agent_type="report_writer",
            parameters={},
            dependencies=["analyze_data", "visualize_results"]
        )
    ]
)
```

By following these tutorials and examples, you can implement sophisticated multi-agent collaboration workflows in the
Agentic Kernel system, enabling agents to work together to solve complex problems.