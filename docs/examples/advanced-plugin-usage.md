# Example: Advanced Plugin Usage in Workflows

The Agentic Kernel's plugins provide reusable capabilities that can be easily integrated into workflows. This example demonstrates how to combine multiple plugins (`FileSurferPlugin` and `WebSurferPlugin`) and use them conditionally within a single orchestrated workflow.

## Scenario

We want to create a workflow that:

1. Checks if a specific configuration file (`settings.json`) exists in a designated directory.
2. If the file exists, reads its content.
3. Extracts a specific setting (e.g., `api_version`) from the configuration data.
4. Searches the web for documentation related to that specific API version.

## Required Plugins/Agents

* `FileSurferAgent`: An agent utilizing the `FileSurferPlugin` (configured with a safe `base_path`). Needs capabilities for checking file existence and reading files.
* `DataExtractorAgent`: A simple agent (or potentially a function within the workflow logic if simple enough) to parse JSON and extract a value.
* `WebSearchAgent`: An agent utilizing the `WebSurferPlugin` for web searches.

## Plan: Combining and Conditioning Plugins

1. **Step 1: Check File Existence**
    * Agent: `FileSurferAgent`
    * Task: Check if `settings.json` exists.
    * Outputs: `file_found` (boolean).
2. **Step 2: Read File (Conditional)**
    * Agent: `FileSurferAgent`
    * Task: Read `settings.json`.
    * **Condition:** Only run if `file_found` from Step 1 is `True`.
    * Outputs: `config_content` (string).
3. **Step 3: Extract Setting (Conditional)**
    * Agent: `DataExtractorAgent` (or internal logic)
    * Task: Parse `config_content` and extract the `api_version` value.
    * **Condition:** Only run if Step 2 completed successfully (implicitly depends on Step 1 being true).
    * Inputs: `config_content`.
    * Outputs: `api_version_value`.
4. **Step 4: Search Documentation (Conditional)**
    * Agent: `WebSearchAgent`
    * Task: Search web for documentation related to the extracted `api_version_value`.
    * **Condition:** Only run if Step 3 completed successfully.
    * Inputs: `api_version_value` (used to formulate the search query).
    * Outputs: `search_results`.

## Conceptual Code Example

```python
import asyncio
import json
from agentic_kernel.types import Task, Workflow, WorkflowStep, Condition
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent

# Assume necessary agents/plugins are registered and configured
# orchestrator = OrchestratorAgent(...)
# file_agent = FileSurferAgent(base_path="./temp_plugin_dir")
# web_agent = WebSearchAgent()
# # A simple agent or function to extract data
# class DataExtractorAgent(BaseAgent):
#     async def execute_task(self, task: Task) -> Any:
#         content = task.inputs.get('json_content')
#         key = task.inputs.get('key_to_extract')
#         try:
#             data = json.loads(content)
#             return {f"{key}_value": data.get(key)}
#         except Exception:
#             return {f"{key}_value": None}
# data_extractor_agent = DataExtractorAgent()
# orchestrator.register_agent(file_agent)
# orchestrator.register_agent(web_agent)
# orchestrator.register_agent(data_extractor_agent)

async def run_advanced_plugin_workflow(simulate_file_exists: bool):

    goal = "Find config, extract API version, and search for its docs."
    config_filename = "settings.json"
    setting_key = "api_version"

    # --- Simulate file creation if needed for the test ---
    # if simulate_file_exists:
    #     # Ensure base_path dir exists
    #     # Path(file_agent.base_path).mkdir(exist_ok=True)
    #     # (Path(file_agent.base_path) / config_filename).write_text(
    #     #     json.dumps({"api_version": "v3.1", "feature_flag": True})
    #     # )
    #     pass 
    # else:
    #     # Ensure file doesn't exist
    #     # try:
    #     #     (Path(file_agent.base_path) / config_filename).unlink()
    #     # except FileNotFoundError:
    #     #     pass
    #     pass
    # ------------------------------------------------------

    steps = [
        # Step 1: Check file existence using FileSurferAgent
        WorkflowStep(
            step_id="check_settings_file",
            task=Task(
                description=f"Check if {config_filename} exists",
                agent_id="FileSurferAgent",
                inputs={"file_path": config_filename, "check_type": "exists"}
            ),
            outputs={"exists_output": "file_found"} # Output: true/false
        ),
        # Step 2: Read file if it exists
        WorkflowStep(
            step_id="read_settings_file",
            task=Task(
                description=f"Read {config_filename}",
                agent_id="FileSurferAgent",
                inputs={"file_path": config_filename, "action": "read"}
            ),
            condition=Condition(step_id="check_settings_file", output_key="file_found", expected_value=True),
            outputs={"read_output": "config_content"} # Output: file content as string
        ),
        # Step 3: Extract the setting value if file was read
        WorkflowStep(
            step_id="extract_api_version",
            task=Task(
                description=f"Extract {setting_key} from config",
                agent_id="DataExtractorAgent",
                inputs={"json_content": "config_content", "key_to_extract": setting_key}
            ),
            # Implicit condition: only runs if 'config_content' is available from step 2
            condition=Condition(step_id="read_settings_file", status="completed"), # Or check output exists
            outputs={f"{setting_key}_value": "api_version_value"} # Output: e.g., "v3.1"
        ),
        # Step 4: Search web using the extracted value if available
        WorkflowStep(
            step_id="search_web_docs",
            task=Task(
                description="Search web for API version documentation",
                agent_id="WebSearchAgent",
                # Agent needs logic to formulate query from input
                inputs={"search_topic_key": "api_version_value"} 
            ),
            condition=Condition(step_id="extract_api_version", status="completed"), # Or check output exists
            outputs={"search_results_output": "search_results"}
        ),
    ]

    workflow = Workflow(
        workflow_id="plugin_chain_demo",
        description=goal,
        steps=steps
    )

    print(f"Starting workflow: {goal}")
    print(f"Simulating file exists: {simulate_file_exists}\n")

    # --- Orchestrator Execution (Simulation) ---
    # result = await orchestrator.execute_workflow(workflow)

    print("--- Orchestrator Internals (Conceptual) ---")
    # ... Simulate execution step-by-step, checking conditions ...
    # (Detailed simulation omitted for brevity, concept is similar to conditional example)
    if simulate_file_exists:
        print("Step 1 (check_file): Completed, file_found=True")
        print("Step 2 (read_file): Condition met, Completed, config_content='{\"api_version\": \"v3.1\", ...}'")
        print("Step 3 (extract_version): Condition met, Completed, api_version_value='v3.1'")
        print("Step 4 (search_web): Condition met, Completed, search_results=[...]")
        final_status = "Completed Successfully"
    else:
        print("Step 1 (check_file): Completed, file_found=False")
        print("Step 2 (read_file): Condition not met, Skipped")
        print("Step 3 (extract_version): Condition not met, Skipped")
        print("Step 4 (search_web): Condition not met, Skipped")
        final_status = "Completed (File Not Found)"
    print("--- End Orchestrator Internals ---")

    print(f"\nWorkflow {final_status}.")

# To run this conceptual example:
# print("\n--- Running Simulation: File Exists ---")
# asyncio.run(run_advanced_plugin_workflow(simulate_file_exists=True))
# print("\n--- Running Simulation: File Does NOT Exist ---")
# asyncio.run(run_advanced_plugin_workflow(simulate_file_exists=False))

# Note: This example highlights chaining multiple plugins/agents and using 
# conditional execution based on the results provided by those plugins.
# Real implementation requires robust agents/plugins and the orchestrator's 
# condition evaluation logic.
```

## Key Takeaways

* Workflows can seamlessly integrate steps using different plugins (FileSurfer, WebSurfer, custom logic).
* Conditional logic (`WorkflowStep.condition`) allows steps to be skipped based on the outcomes of previous plugin-driven steps.
* The input/output mapping mechanism ensures data flows correctly between steps, even when those steps use different underlying plugins or agents.
* This enables building sophisticated automation pipelines by combining specialized, reusable plugin capabilities. 
