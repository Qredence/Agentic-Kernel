# ADK Multi-Agent Example

This example demonstrates a simple multi-agent system using components from the Agentic Kernel, inspired by Google's ADK framework and concepts from Agent-to-Agent (A2A) communication.

## Features

- **Task Manager Agent**: Coordinates and delegates tasks.
- **Worker Agent**: Executes assigned tasks.
- **Validator Agent**: Validates completed task results.
- **Coordination Manager**: Manages task states (planned, scheduled, in_progress, completed) across agents.
- **Trust Manager**: Tracks trust scores for agents based on task validation.

## Structure

```
adk_multi_agent/
├── agents/
│   ├── __init__.py
│   ├── task_manager.py
│   ├── worker.py
│   └── validator.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_base_agent.py
│   ├── test_task_manager.py
│   ├── test_worker.py
│   ├── test_validator.py
│   └── test_main.py
├── utils/
│   ├── __init__.py
│   └── base_agent.py # Contains a base Agent class for this example
├── __init__.py
├── main.py             # Main script to run the example flow
├── pytest.ini          # Pytest configuration
├── requirements.txt    # Project dependencies
└── README.md
```

## Setup

1.  **Install Dependencies:** Ensure you have `uv` installed. From the workspace root (`Agentic-Kernel`), install the required packages:
    ```bash
    uv pip install -r examples/adk_multi_agent/requirements.txt
    ```

## Running the Example

From the workspace root (`Agentic-Kernel`), run:

```bash
python examples/adk_multi_agent/main.py
```

You should see log output detailing the interaction:

1.  The `main` script initializes shared `CoordinationManager` and `TrustManager` instances.
2.  It creates the `TaskManagerAgent`, `WorkerAgent`, and `ValidatorAgent`, injecting the shared managers.
3.  **Task Manager**: Creates a task and immediately schedules it using the `CoordinationManager`.
4.  **Worker Agent**: Executes the task, updating its status to `IN_PROGRESS` and then `COMPLETED` via the `CoordinationManager`.
5.  **Validator Agent**: Validates the completed task by checking its status in the `CoordinationManager`.
6.  **Validator Agent**: Updates the `TrustManager` based on the validation result.

## Testing

The example includes unit/integration tests for the agents and the main flow.

From the workspace root (`Agentic-Kernel`), ensure your virtual environment is activated and run:

```bash
python -m pytest -v examples/adk_multi_agent/tests/
```

(Note: You may see Pydantic V1 deprecation warnings, which are expected for now).