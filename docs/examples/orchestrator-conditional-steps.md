# Example: Orchestrator Conditional Steps

Workflows often need to adapt their path based on intermediate results. The Agentic Kernel allows defining conditional logic within workflows, enabling steps to be executed or skipped based on the outcome of previous steps.

## Scenario

Let's create a workflow that checks if a configuration file (`config.json`) exists:

* **If it exists:** Read the configuration file.
* **If it doesn't exist:** Create a default configuration file.
* **Finally:** Use the configuration (either read or default).

## Plan with Conditions

1. **Step 1: Check File Existence**
    * Use a `FileSurferAgent` to check if `config.json` exists in a specified directory.
    * Output: `file_exists` (boolean).
2. **Step 2: Read Existing Config (Conditional)**
    * **Condition:** Execute this step *only if* `file_exists` from Step 1 is `True`.
    * Use `FileSurferAgent` to read `config.json`.
    * Output: `config_data`.
3. **Step 3: Create Default Config (Conditional)**
    * **Condition:** Execute this step *only if* `file_exists` from Step 1 is `False`.
    * Use `FileSurferAgent` (or another agent) to create `config.json` with default content.
    * Output: `config_data`.
4. **Step 4: Use Config**
    * Use an agent (e.g., `ConfigUserAgent`) that takes `config_data` as input.
    * Input: The `config_data` output from *either* Step 2 *or* Step 3 (whichever executed).

## Conceptual Code Example

This example shows how `WorkflowStep` conditions might be defined. Assume `FileSurferAgent` and `ConfigUserAgent` are registered.

```python
import asyncio
from agentic_kernel.types import Task, Workflow, WorkflowStep, Condition
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent is the main class

# Assume agents are registered and orchestrator is initialized
# orchestrator = OrchestratorAgent(...)
# file_agent = FileSurferAgent(base_path="./temp_config_dir") # Needs a safe base path
# config_user_agent = ConfigUserAgent()
# orchestrator.register_agent(file_agent)
# orchestrator.register_agent(config_user_agent)

# Helper to create default config content
def create_default_config():
    import json
    return json.dumps({"setting": "default", "value": 1})

async def run_conditional_workflow_example(simulate_file_exists: bool):

    goal = "Ensure config file exists and use its settings."
    config_filename = "config.json"

    # Define the steps with conditions
    steps = [
        WorkflowStep(
            step_id="check_file",
            task=Task(
                description=f"Check if {config_filename} exists", 
                agent_id="FileSurferAgent", 
                # Agent needs specific input for file checking
                inputs={"file_path": config_filename, "check_type": "exists"} 
            ),
            outputs={"exists_output": "file_exists"}
        ),
        WorkflowStep(
            step_id="read_config",
            task=Task(
                description=f"Read existing {config_filename}", 
                agent_id="FileSurferAgent",
                inputs={"file_path": config_filename, "action": "read"}
            ),
            # Condition: Only run if step 'check_file' output 'file_exists' is True
            condition=Condition(step_id="check_file", output_key="file_exists", expected_value=True),
            outputs={"read_output": "config_data"} # Output key for the final step
        ),
        WorkflowStep(
            step_id="create_config",
            task=Task(
                description=f"Create default {config_filename}", 
                agent_id="FileSurferAgent",
                # Agent needs specific input for writing
                inputs={"file_path": config_filename, "content": create_default_config(), "action": "write"}
            ),
            # Condition: Only run if step 'check_file' output 'file_exists' is False
            condition=Condition(step_id="check_file", output_key="file_exists", expected_value=False),
            outputs={"write_output": "config_data"} # Output key for the final step
        ),
        WorkflowStep(
            step_id="use_config",
            task=Task(
                description="Use the configuration data", 
                agent_id="ConfigUserAgent"
            ),
            # Input: Takes 'config_data' from either 'read_config' or 'create_config'
            # The orchestrator handles mapping the correct output based on which step ran.
            inputs={"config_input": "config_data"}, 
            outputs={"usage_result": "final_output"}
        ),
    ]

    workflow = Workflow(
        workflow_id="conditional_config_demo",
        description=goal,
        steps=steps
    )

    print(f"Starting workflow for: {goal}")
    print(f"Simulating file exists: {simulate_file_exists}\n")

    # --- Orchestrator Execution (Simulation) ---
    # This requires the actual Orchestrator logic that evaluates conditions
    # based on the results stored in the ProgressLedger.

    # result = await orchestrator.execute_workflow(workflow)

    print("--- Orchestrator Internals (Conceptual) ---")
    print("Step 1 'check_file': Executing...")
    step1_output = {"file_exists": simulate_file_exists}
    print(f"-> Result: {step1_output}")

    step2_result = {"status": "skipped"}
    step3_result = {"status": "skipped"}
    final_config_data = None

    # Evaluate conditions based on Step 1 result
    if step1_output["file_exists"] == True:
        print("Condition MET for Step 2 'read_config': Executing...")
        # Simulate reading
        step2_result = {"status": "completed", "output": {"config_data": {"setting": "custom", "value": 123}}}
        final_config_data = step2_result["output"]["config_data"]
        print(f"-> Result: {step2_result}")
        print("Condition NOT MET for Step 3 'create_config': Skipping.")
    else:
        print("Condition NOT MET for Step 2 'read_config': Skipping.")
        print("Condition MET for Step 3 'create_config': Executing...")
        # Simulate creating
        step3_result = {"status": "completed", "output": {"config_data": json.loads(create_default_config())}}
        final_config_data = step3_result["output"]["config_data"]
        print(f"-> Result: {step3_result}")

    print("\nStep 4 'use_config': Executing...")
    # Simulate using the config
    step4_result = {"status": "completed", "output": {"final_output": f"Used config: {final_config_data}"}}
    print(f"-> Result: {step4_result}")
    print("--- End Orchestrator Internals ---")

    # Construct final placeholder result
    final_result_placeholder = {
        "check_file": {"status": "completed", "output": step1_output},
        "read_config": step2_result,
        "create_config": step3_result,
        "use_config": step4_result,
    }

    print("\nWorkflow completed.")
    print("Final Result (Conceptual):")
    import json
    print(json.dumps(final_result_placeholder, indent=2))


# Example Runs
# print("--- Running Simulation: File Exists ---")
# asyncio.run(run_conditional_workflow_example(simulate_file_exists=True))
# print("\n--- Running Simulation: File Does NOT Exist ---")
# asyncio.run(run_conditional_workflow_example(simulate_file_exists=False))

# Note: The `Condition` class and the Orchestrator's logic to evaluate it against 
# the `ProgressLedger` are key here. The Orchestrator needs to check the specified 
# output of the dependency step before deciding whether to execute the conditional step.
```

## Key Takeaways

* `WorkflowStep` can include a `condition` parameter.
* The `condition` typically references an output from a previous step and an expected value.
* The Orchestrator evaluates these conditions during execution using the results stored in the `ProgressLedger`.
* Steps whose conditions are not met are marked as `skipped`.
* This allows for creating flexible workflows that branch based on dynamic data or outcomes.
