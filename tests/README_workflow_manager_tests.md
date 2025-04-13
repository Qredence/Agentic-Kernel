# WorkflowManager Tests

This document describes the tests for the `WorkflowManager` class in the Agentic Kernel project.

## Overview

The `WorkflowManager` class is responsible for managing workflow execution and lifecycle. It integrates with the dynamic
capability registry and provides features for workflow persistence, resource management, workflow templates, and
enhanced error handling.

## Test Structure

The tests are organized in the `test_workflow_manager.py` file and follow the pytest testing framework. They use
fixtures to create mock dependencies and test instances, and they use pytest's asyncio support for testing async
functions.

## Fixtures

The following fixtures are defined:

- `mock_capability_registry`: Creates a mock `DynamicCapabilityRegistry` for testing.
- `mock_agent`: Creates a mock `BaseAgent` for testing.
- `workflow_manager`: Creates a `WorkflowManager` instance with mock dependencies.
- `workflow_template`: Creates a sample workflow template for testing.
- `sample_workflow_steps`: Creates sample workflow steps for testing.

## Tests

The tests cover the following functionality:

### Agent Management

- `test_register_agent`: Tests registering an agent with the workflow manager.
- `test_discover_agents`: Tests discovering agents with specific capabilities.

### Workflow Template Management

- `test_register_workflow_template`: Tests registering a workflow template.
- `test_create_workflow_from_template`: Tests creating a workflow from a template.
- `test_workflow_template_instantiation`: Tests instantiating a workflow template with parameters.
- `test_workflow_template_with_missing_required_parameter`: Tests instantiating a template with a missing required
  parameter.
- `test_workflow_template_with_default_parameter`: Tests instantiating a template with default parameter values.

### Workflow Execution

- `test_execute_workflow`: Tests executing a workflow.
- `test_execute_workflow_with_failure`: Tests executing a workflow with a failing step.
- `test_execute_workflow_with_timeout`: Tests executing a workflow with a timeout.

### Persistence

- `test_workflow_persistence`: Tests persisting and loading workflow state.

## Running the Tests

To run the tests, you would normally use pytest:

```bash
pytest tests/test_workflow_manager.py -v
```

However, due to issues with the project's codebase, the tests cannot be run directly. Instead, they serve as
documentation for how the `WorkflowManager` class should be tested.

## Test Coverage

The tests cover all the main functionalities of the `WorkflowManager` class:

1. Registering agents
2. Discovering agents
3. Registering workflow templates
4. Creating workflows from templates
5. Executing workflows (with success, failure, and timeout scenarios)
6. Persisting and loading workflow state
7. Workflow template instantiation (with parameter substitution, missing required parameters, and default parameters)

## Future Improvements

Future improvements to the tests could include:

1. Testing more edge cases, such as:
    - Executing a workflow with no steps
    - Executing a workflow with circular dependencies
    - Executing a workflow with invalid agent types
    - Executing a workflow with invalid parameters

2. Testing more advanced features, such as:
    - Workflow replanning
    - Conditional branching
    - Parallel execution
    - Resource optimization

3. Adding integration tests that test the `WorkflowManager` with real dependencies instead of mocks.