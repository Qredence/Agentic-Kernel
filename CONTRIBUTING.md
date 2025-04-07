# Contributing to Agentic Kernel

Thank you for your interest in contributing to Agentic Kernel! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Workflow](#workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

We expect all contributors to adhere to our code of conduct, which promotes a welcoming and inclusive environment. Please be respectful, considerate, and constructive in all interactions.

## Getting Started

1. **Fork the repository**: Start by forking the [Agentic Kernel repository](https://github.com/your-organization/agentic-kernel).
2. **Clone the fork**: Clone your fork to your local machine.
3. **Set up the development environment**: Follow the instructions in the [Development Environment](#development-environment) section.

## Development Environment

### Prerequisites

- Python 3.10 or higher
- uv (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/agentic-kernel.git
   cd agentic-kernel
   ```

2. Create and activate a virtual environment with uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   uv pip install -e ".[dev]"
   ```

## Workflow

1. **Create a branch**: Create a branch for your changes.
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**: Implement your changes, following the [Coding Standards](#coding-standards).

3. **Test**: Run tests to ensure your changes don't break existing functionality.
   ```bash
   pytest
   ```

4. **Document**: Update documentation as necessary.

5. **Commit**: Commit your changes with a descriptive commit message.
   ```bash
   git commit -m "Add feature X"
   ```

6. **Push**: Push your changes to your fork.
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Pull Request**: Create a pull request from your fork to the main repository.

## Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- Use [type hints](https://www.python.org/dev/peps/pep-0484/) for all functions and methods.
- Write docstrings for all modules, classes, functions, and methods.
- Use meaningful variable and function names.
- Keep functions and methods short and focused.
- Use `ruff` for linting and formatting to ensure consistent code style.

### Code Style

- Use 4 spaces for indentation.
- Use single quotes for strings unless the string contains single quotes.
- Use f-strings for string formatting.
- Keep line length to 88 characters (enforced by ruff).
- Add comments for complex code or non-obvious behavior.

## Testing

- Write tests for all new features and bug fixes.
- Follow test-driven development (TDD) principles when appropriate.
- Use pytest for unit and integration tests.
- Run the full test suite before submitting changes.
- Aim for high test coverage, especially for critical components.

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src/agentic_kernel

# Run specific tests
pytest tests/test_orchestrator.py
```

## Documentation

- Update documentation for any changes to APIs or behavior.
- Document all public functions, classes, and modules.
- Use clear language and provide examples where appropriate.
- Keep documentation up-to-date with code changes.

### Documentation Standards

- Write docstrings in Google style.
- Include parameter descriptions, return values, and raised exceptions.
- Add examples for complex functions or classes.
- Update README.md, ARCHITECTURE.md, and other documentation files as needed.

Example docstring:

```python
def create_dynamic_workflow(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[WorkflowStep]:
    """Create a dynamic workflow for a given goal.
    
    Args:
        goal: The goal to create a workflow for.
        context: Optional context information for planning.
        
    Returns:
        A list of WorkflowStep objects representing the workflow.
        
    Raises:
        ValueError: If the goal is empty or invalid.
    
    Example:
        ```python
        workflow = await orchestrator.create_dynamic_workflow("Research quantum computing")
        result = await orchestrator.execute_workflow(workflow)
        ```
    """
```

## Submitting Changes

1. **Pull Request**: Submit a pull request from your fork to the main repository.
2. **Description**: Include a detailed description of your changes.
3. **Issue Reference**: Reference any related issues.
4. **Tests**: Ensure all tests pass and code style checks pass.
5. **Review**: Address any feedback from code reviews.
6. **CI/CD**: Wait for CI/CD pipelines to complete successfully.
7. **Merge**: Once approved, your changes will be merged into the main branch.

## Working with the Orchestrator

If you're contributing to the Orchestrator component, please review the [Orchestrator Developer Guide](docs/developer/orchestrator.md) for detailed information on the architecture and extension points.

Key areas to consider when modifying the Orchestrator:

1. **Nested Loop Architecture**: Understand the separation of planning (outer loop) and execution (inner loop) concerns.
2. **Error Recovery**: Maintain or improve error recovery mechanisms.
3. **Progress Monitoring**: Ensure accurate progress tracking.
4. **Agent Integration**: Follow the established patterns for agent registration and delegation.

## Thank You!

Your contributions help improve Agentic Kernel for everyone. We appreciate your time and effort! 