# Testing Guide

## Overview

The project uses `pytest` and `pytest-asyncio` for testing. Tests are organized in the `tests/` directory at the project root.

## Test Structure

### Unit Tests

Unit tests are written for individual components and are located in files named `test_*.py`. Each test file corresponds to a specific module in the codebase.

Current test coverage includes:

- `test_orchestrator.py`: Tests for the OrchestratorAgent
  - Basic initialization and configuration
  - Agent registration
  - Workflow execution (empty, single step, failures)
  - Retry logic
  - Progress calculation

### Test Categories

1. **Basic Tests**
   - Component initialization
   - Configuration validation
   - Simple method calls

2. **Integration Tests**
   - Workflow execution
   - Agent interactions
   - Ledger operations

3. **Async Tests**
   - Proper async/await patterns
   - Concurrent operations
   - Timeout handling

## Running Tests

To run the tests:

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_orchestrator.py

# Run with verbose output
uv run pytest -v tests/test_orchestrator.py
```

## Mocking Strategy

The project uses Python's `unittest.mock` library, specifically:
- `MagicMock` for synchronous dependencies
- `AsyncMock` for asynchronous dependencies

Example mock setup:
```python
@pytest.fixture
def mock_agent():
    agent = AsyncMock(spec=BaseAgent)
    agent.type = "test_agent"
    agent.execute = AsyncMock(return_value={"status": "success"})
    return agent
```

## Test Development Guidelines

1. **Async Testing**
   - Use `@pytest.mark.asyncio` for async tests
   - Properly mock async dependencies
   - Handle coroutines correctly

2. **Mocking**
   - Use `spec` parameter to ensure mock matches interface
   - Mock at the appropriate level
   - Verify mock interactions

3. **Test Organization**
   - Clear, descriptive test names
   - Comprehensive docstrings
   - Logical test grouping

4. **Assertions**
   - Use precise assertions
   - Include helpful failure messages
   - Test both success and failure cases

## Future Improvements

- [ ] Add end-to-end testing
- [ ] Implement performance benchmarks
- [ ] Add test coverage reporting
- [ ] Create more comprehensive integration tests 