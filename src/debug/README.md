# Debug Tools

This directory contains debugging tools for the Agentic Kernel project.

## Available Tools

### 1. Debug App (`debug_app.py`)
A validation script that tests imports and initialization of key components.

**Usage:**
```python
from agentic_kernel.debug import run_debug_app

# Run the debug validation
exit_code = run_debug_app()
```

### 2. Simple Debug (`simple_debug.py`)
A Chainlit-based debug application for interactive testing of the Agentic Kernel.

**Features:**
- Import validation
- Component initialization testing
- Interactive chat interface
- Basic workflow testing

**Usage:**
```python
from agentic_kernel.debug import test_imports, run_debug_workflow

# Test imports and initialization
success = test_imports()

# Run the debug workflow
await run_debug_workflow()
```

**Running the Chainlit App:**
```bash
chainlit run src/debug/simple_debug.py -w
```

## Development Guidelines

1. Keep debug tools focused and single-purpose
2. Add comprehensive logging
3. Include clear error messages
4. Document all new debug tools in this README
5. Use absolute imports from the project root
6. Add type hints and docstrings

## Adding New Debug Tools

When adding new debug tools:
1. Create your debug script in this directory
2. Add imports to `__init__.py`
3. Update this README with usage instructions
4. Include appropriate error handling and logging 