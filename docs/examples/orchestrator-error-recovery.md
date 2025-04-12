# Example: Orchestrator Error Recovery

Workflows don't always execute perfectly. Network issues, unavailable services, or invalid inputs can cause steps to fail. The Agentic Kernel's Orchestrator includes mechanisms for error handling and recovery, such as automatic retries or executing alternative steps.

## Scenario

Consider a workflow that needs to fetch data from an external API, which might occasionally be unreliable.

1.  **Plan:**
    *   Step 1: Fetch data from `https://api.unreliable-service.com/data` (using a Web Request Agent/Plugin).
    *   Step 2: Process the fetched data.

2.  **Error Encountered:** The first attempt to execute Step 1 fails due to a network timeout.

3.  **Orchestrator Recovery:**
    *   **Retry:** The Orchestrator, based on configuration (e.g., max retries), automatically retries Step 1.
    *   **Success (on retry):** The second attempt succeeds, and the workflow proceeds to Step 2.
    *   **Failure (alternative):** If retries are exhausted, the Orchestrator might mark the step as failed and potentially trigger a predefined error handling path or stop the workflow, depending on the workflow definition.

## Conceptual Code Example

This example focuses on the retry mechanism. Assume a `WebRequestAgent` is registered.

```python
import asyncio
from agentic_kernel.types import Task, Workflow, WorkflowStep
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent is the main class

# Assume agents are registered and orchestrator is initialized
# orchestrator = OrchestratorAgent(max_step_retries=2) # Configure max retries
# web_agent = WebRequestAgent() # This agent would internally handle HTTP requests
# data_processor_agent = DataProcessorAgent()
# orchestrator.register_agent(web_agent)
# orchestrator.register_agent(data_processor_agent)

async def run_error_recovery_example():

    goal = "Fetch data from an external service and process it."

    steps = [
        WorkflowStep(
            step_id="fetch_data",
            task=Task(
                description="Fetch data from unreliable service", 
                agent_id="WebRequestAgent",
                inputs={"url": "https://api.unreliable-service.com/data"} # Agent input
            ),
            outputs={"api_response": "raw_data"}
        ),
        WorkflowStep(
            step_id="process_data",
            task=Task(
                description="Process the fetched data", 
                agent_id="DataProcessorAgent"
            ),
            inputs={"raw_data": "api_response"}, # Input from previous step
            outputs={"processed_result": "final_data"}
        ),
    ]

    workflow = Workflow(
        workflow_id="error_recovery_demo",
        description=goal,
        steps=steps
    )

    print(f"Starting workflow for: {goal}")

    # --- Orchestrator Execution (Simulation) ---
    print("\n--- Orchestrator Internals (Conceptual) ---")
    print("Attempt 1: Executing Step 1 'fetch_data'...")
    print("-> Failure detected (e.g., Timeout)!")

    # Orchestrator checks retry policy (e.g., max_step_retries = 2)
    print("Orchestrator: Retrying Step 1 (Attempt 2)...")
    print("Attempt 2: Executing Step 1 'fetch_data'...")
    print("-> Success! Data fetched.")
    step1_result = {"status": "completed", "output": {"api_response": {"value": 123}}}
    print(f"Step 1 Result: {step1_result}")

    print("\nExecuting Step 2 'process_data' with input from Step 1...")
    # Simulate processing
    step2_result = {"status": "completed", "output": {"processed_result": "Processed value: 123"}}
    print(f"Step 2 Result: {step2_result}")
    print("--- End Orchestrator Internals ---")

    # Combine results conceptually
    final_result_placeholder = {
        "fetch_data": step1_result,
        "process_data": step2_result
    }

    print("\nWorkflow completed successfully after retry.")
    print("Final Result (Conceptual):")
    import json
    print(json.dumps(final_result_placeholder, indent=2))

# To run this conceptual example:
# asyncio.run(run_error_recovery_example())

# Note: The actual error detection, retry logic, and state management happen within the 
# OrchestratorAgent. Configuration options likely control retry behavior (e.g., number of 
# retries, backoff delays). More complex error handling might involve conditional 
# branches defined within the workflow itself.
```

## Key Takeaways

*   The Orchestrator can be configured to automatically retry failed steps.
*   This improves the resilience of workflows that depend on potentially unreliable external factors.
*   Retry limits prevent infinite loops.
*   More advanced error handling (e.g., executing alternative steps) can be built into the workflow logic or Orchestrator configuration. 
