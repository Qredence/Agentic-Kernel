# Example: Workflow Optimization Usage

The Agentic Kernel includes a Workflow Optimizer designed to analyze past workflow executions and suggest improvements. This can involve parallelizing steps, choosing more efficient agents, or tuning parameters based on historical performance.

**Note:** Optimization typically requires historical execution data for a workflow. The optimizer analyzes patterns in this data (e.g., which steps take the longest, which agents succeed most often for certain tasks) to propose changes.

## Scenario

Imagine you have a workflow (`data_pipeline_v1`) that runs regularly to fetch, process, and report on some data. After several runs, you suspect it could be more efficient.

1.  **Execute Workflow:** Run the workflow (`data_pipeline_v1`) multiple times to generate execution history.
2.  **Trigger Optimization:** Use the Orchestrator's optimization capability to analyze the history of `data_pipeline_v1`.
3.  **Get Optimized Version:** The optimizer analyzes the history and might create a new version (`data_pipeline_v2`) with changes (e.g., parallelizing independent fetching steps, assigning a faster agent to a processing step).
4.  **Compare (Optional):** Compare the projected or actual performance metrics between `v1` and `v2`.
5.  **Execute Optimized Workflow:** Run the new, optimized version (`data_pipeline_v2`).

## Required Components

*   `OrchestratorAgent`: Contains the `optimize_workflow` and potentially comparison methods. It needs access to historical execution data (likely via the `ProgressLedger` or a dedicated history store).
*   `WorkflowOptimizer`: The internal component doing the analysis (multiple strategies like `ParallelizationOptimizer`, `AgentSelectionOptimizer`).
*   Historical Execution Data: Stored results and metrics from previous runs of the workflow being optimized.

## Conceptual Code Example

This example shows the user-facing interaction points, not the internal optimization logic.

```python
import asyncio
from agentic_kernel.types import Workflow # Assuming Workflow definition
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent

# Assume orchestrator is initialized and has access to execution history
# orchestrator = OrchestratorAgent(history_store=...)

# Assume 'data_pipeline_v1' Workflow object exists and has been run previously
# existing_workflow: Workflow = load_workflow_definition("data_pipeline_v1")

async def run_optimization_example():

    workflow_id_to_optimize = "data_pipeline_v1"

    print(f"Attempting to optimize workflow: {workflow_id_to_optimize}")

    # --- Trigger Optimization --- 
    # This call invokes the WorkflowOptimizer within the orchestrator
    try:
        # optimization_result = await orchestrator.optimize_workflow(workflow_id_to_optimize)

        # --- Simulation of Optimization Result ---
        print("\n--- Orchestrator Internals (Conceptual) ---")
        print(f"Analyzing execution history for '{workflow_id_to_optimize}'...")
        print("Identified potential parallelization for steps A and B.")
        print("Identified AgentX is faster than AgentY for step C based on history.")
        print("Creating new optimized workflow version...")
        optimization_result = {
            "original_workflow_id": workflow_id_to_optimize,
            "optimized_workflow_id": "data_pipeline_v2", # New ID for the optimized version
            "version_id": "v2",
            "summary": "Parallelized steps A & B. Reassigned step C to AgentX.",
            "status": "success"
        }
        print("--- End Orchestrator Internals ---")
        # ----------------------------------------

        if optimization_result and optimization_result.get("status") == "success":
            optimized_workflow_id = optimization_result["optimized_workflow_id"]
            print(f"\nOptimization successful! Created new version: {optimized_workflow_id}")
            print(f"Summary: {optimization_result.get('summary')}")

            # --- Optional: Compare Versions (Conceptual) ---
            # comparison = await orchestrator.compare_optimized_version(
            #     workflow_id=workflow_id_to_optimize, # Original ID
            #     original_version_id="v1", 
            #     optimized_version_id=optimization_result["version_id"]
            # )
            # print(f"\nComparison:
{comparison}")
            # --------------------------------------------

            # --- Execute the Optimized Workflow ---
            print(f"\nExecuting optimized workflow: {optimized_workflow_id}")
            # optimized_workflow_def = load_workflow_definition(optimized_workflow_id)
            # execution_result = await orchestrator.execute_workflow(optimized_workflow_def)
            print("(Simulation) Optimized workflow execution completed.")
            # --------------------------------------

        else:
            print("\nWorkflow optimization failed or yielded no improvements.")
            # Reason might be in optimization_result

    except Exception as e:
        # Handle cases where optimization might fail (e.g., no history)
        print(f"\nError during optimization: {e}")

# To run this conceptual example:
# asyncio.run(run_optimization_example())

# Note: The core logic resides in the `WorkflowOptimizer` and its strategies.
# This example shows how a user might interact with the optimization feature via the Orchestrator.
# Effective optimization relies heavily on sufficient and accurate execution history.
```

## Key Takeaways

*   Workflow optimization is typically triggered explicitly via the Orchestrator.
*   It analyzes *past* execution data (metrics, successes, failures) of a specific workflow.
*   The process aims to generate a *new version* of the workflow with structural or configuration changes.
*   Optimization strategies can include parallelization, agent reassignment, parameter tuning, etc.
*   Users can then choose to execute the new, potentially more efficient, workflow version. 
