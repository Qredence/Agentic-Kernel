# Example: Agent Communication in Workflows

A key strength of the Agentic Kernel is its ability to orchestrate multiple specialized agents to achieve a complex goal. This requires seamless communication, where the output of one agent becomes the input for the next. The Orchestrator manages this data flow using the `inputs` and `outputs` defined in each `WorkflowStep`.

## Scenario

Let's build a workflow to:

1. Search the web for a specific topic (e.g., "agentic design patterns").
2. Take the URL of the *first* search result.
3. Summarize the content of that webpage.

This involves two agents:

* `WebSearchAgent`: Performs the search and returns a list of results (including URLs).
* `SummarizerAgent`: Takes a URL and returns a text summary.

## Plan: Linking Steps via Inputs/Outputs

1. **Step 1: Search Web**
    * Agent: `WebSearchAgent`
    * Task: Search for "agentic design patterns".
    * **Outputs:** Define an output named `search_outcome`. The `WebSearchAgent` should be designed to return data structured in a way that the orchestrator can extract the needed pieces (e.g., a dictionary containing a key like `first_result_url`). We map the agent's specific output key (`first_result_url`) to the workflow variable `target_url`. So, `outputs = {"first_result_url": "target_url"}`.

2. **Step 2: Summarize Page**
    * Agent: `SummarizerAgent`
    * Task: Summarize the webpage.
    * **Inputs:** This step needs the URL found in Step 1. We map the workflow variable `target_url` (which holds the URL from Step 1) to the input expected by the `SummarizerAgent` (e.g., `url_input`). So, `inputs = {"url_input": "target_url"}`.
    * **Outputs:** `summary_text`.

## Conceptual Code Example

Assume `WebSearchAgent` and `SummarizerAgent` are registered.

```python
import asyncio
from agentic_kernel.types import Task, Workflow, WorkflowStep
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent is the main class

# Assume agents are registered and orchestrator is initialized
# orchestrator = OrchestratorAgent(...)
# search_agent = WebSearchAgent()
# summarize_agent = SummarizerAgent()
# orchestrator.register_agent(search_agent)
# orchestrator.register_agent(summarize_agent)

async def run_agent_communication_example():

    goal = "Search for agentic design patterns and summarize the first result."
    search_topic = "agentic design patterns"

    steps = [
        WorkflowStep(
            step_id="search_step",
            task=Task(
                description=f"Search web for '{search_topic}'", 
                agent_id="WebSearchAgent",
                inputs={"query": search_topic} # Input for the search agent
            ),
            # Map the agent's output key 'first_result_url' to workflow variable 'target_url'
            outputs={"first_result_url": "target_url"} 
        ),
        WorkflowStep(
            step_id="summarize_step",
            task=Task(
                description="Summarize the found webpage", 
                agent_id="SummarizerAgent"
                # The agent expects an input, which we map below
            ),
            # Map workflow variable 'target_url' to the agent's expected input 'url_input'
            inputs={"url_input": "target_url"}, 
            outputs={"summary": "summary_text"}
        ),
    ]

    workflow = Workflow(
        workflow_id="search_summarize_comm_demo",
        description=goal,
        steps=steps
    )

    print(f"Starting workflow for: {goal}")

    # --- Orchestrator Execution (Simulation) ---
    # Actual execution involves the orchestrator managing the data flow based 
    # on the input/output mappings and results stored in the ProgressLedger.

    # result = await orchestrator.execute_workflow(workflow)

    print("\n--- Orchestrator Internals (Conceptual) ---")
    print("Step 1 'search_step': Executing...")
    # Simulate search agent output containing the key we defined in 'outputs'
    step1_output = {"first_result_url": "https://example.com/agentic-patterns"}
    print(f"-> Result: {step1_output}")
    # Orchestrator stores this, mapping 'first_result_url' to 'target_url' internally.

    print("\nStep 2 'summarize_step': Preparing inputs...")
    # Orchestrator looks at inputs for Step 2: {"url_input": "target_url"}
    # It retrieves the value associated with "target_url" from Step 1's output.
    step2_input_value = step1_output["first_result_url"] # Simplified lookup
    print(f"-> Providing input {{'url_input': '{step2_input_value}'}} to SummarizerAgent.")

    print("Step 2 'summarize_step': Executing...")
    # Simulate summarizer agent output
    step2_output = {"summary": "Agentic patterns involve autonomous agents collaborating..."}
    print(f"-> Result: {step2_output}")
    # Orchestrator stores this, mapping 'summary' to 'summary_text'.
    print("--- End Orchestrator Internals ---")

    # Construct final placeholder result
    final_result_placeholder = {
        "search_step": {"status": "completed", "output": step1_output},
        "summarize_step": {"status": "completed", "output": step2_output},
    }

    print("\nWorkflow completed.")
    print("Final Result (Conceptual):")
    import json
    print(json.dumps(final_result_placeholder, indent=2))

# To run this conceptual example:
# asyncio.run(run_agent_communication_example())

# Note: The effectiveness of this relies on agents returning structured output (like dicts) 
# and the Orchestrator using the input/output mappings defined in WorkflowSteps to pass 
# the correct data between steps.
```

## Key Takeaways

* **`outputs` Mapping:** In a `WorkflowStep`, the `outputs` dictionary maps keys from the *agent's* execution result to more general *workflow variable* names.
* **`inputs` Mapping:** The `inputs` dictionary maps *workflow variable* names (which hold data from previous steps' outputs) to the input keys expected by the *current step's agent*.
* **Orchestrator Role:** The Orchestrator acts as the intermediary, using the `ProgressLedger` to store results associated with workflow variable names and providing the required inputs to subsequent agents based on these mappings.
* **Data Flow:** This input/output mapping mechanism enables complex workflows where agents build upon each other's results without needing direct knowledge of one another.
