# Example: Orchestrator Dynamic Planning

The Agentic Kernel's Orchestrator is designed to be adaptive. It doesn't just execute a fixed plan; it can dynamically adjust the workflow based on the results of previous steps or unexpected situations encountered during execution. This allows the system to handle more complex and unpredictable tasks.

## Scenario

Imagine a task to research the current weather in a city *and* find a related news article.

1. **Initial Plan:**
    * Step 1: Get the weather for the specified city (using a Weather Agent/Plugin).
    * Step 2: Search for news articles related to the city (using a Web Search Agent/Plugin).

2. **Dynamic Adjustment:** After getting the weather (e.g., "Rainy in London"), the orchestrator realizes the initial plan is incomplete. To find a *related* news article, it needs to incorporate the weather information into the search query.
    * **New Step (Inserted):** Modify the search query to include the weather condition (e.g., "Rainy London news").
    * **Adjusted Step 2:** Execute the web search with the *new* query.

## Conceptual Code Example

This example shows the high-level interaction. Assume we have `WeatherAgent` and `WebSearchAgent` registered with the `OrchestratorAgent`.

```python
import asyncio
from agentic_kernel.types import Task, Workflow, WorkflowStep
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent is the main class

# Assume agents are registered and orchestrator is initialized
# orchestrator = OrchestratorAgent(...)
# weather_agent = WeatherAgent()
# web_search_agent = WebSearchAgent()
# orchestrator.register_agent(weather_agent)
# orchestrator.register_agent(web_search_agent)

async def run_dynamic_weather_news_task():

    initial_goal = "Get the weather for London and find a related news article."

    # The orchestrator might initially generate a plan like this:
    initial_steps = [
        WorkflowStep(
            step_id="get_weather",
            task=Task(description="Get weather for London", agent_id="WeatherAgent"),
            outputs={"weather_condition": "weather_result"} # Map agent output to this key
        ),
        WorkflowStep(
            step_id="search_news",
            task=Task(description="Search news about London", agent_id="WebSearchAgent"),
            # Input depends on dynamic planning later
            inputs={}, 
            outputs={"news_articles": "search_results"}
        ),
    ]

    workflow = Workflow(
        workflow_id="weather_news_dynamic",
        description=initial_goal,
        steps=initial_steps
    )

    print(f"Starting workflow for: {initial_goal}")

    # --- Orchestrator Execution ---
    # During execution, the orchestrator runs step 1 ('get_weather').
    # Let's say the result is {'weather_result': 'Rainy'}

    # The orchestrator analyzes the next step ('search_news') and the overall goal.
    # It realizes the search needs the weather context.
    # It dynamically modifies the plan:
    # 1. It might add an intermediate step to formulate the new query.
    # 2. It updates the inputs for the 'search_news' step.

    # (Conceptual - Actual implementation is internal to the orchestrator)
    # Orchestrator internally might decide:
    # updated_search_task = Task(
    #     description="Search news about Rainy London", 
    #     agent_id="WebSearchAgent"
    # )
    # workflow.steps[1].task = updated_search_task # Update the task for the step
    # workflow.steps[1].inputs = {"query_topic": "Rainy London"} # Provide input needed by agent

    # Execute the (potentially modified) workflow
    # This is a simplified call; actual execution involves the orchestrator loop
    # result = await orchestrator.execute_workflow(workflow) 

    # --- Placeholder for demonstrating the concept ---
    print("\n--- Orchestrator Internals (Conceptual) ---")
    print("Step 1: Executed 'get_weather'. Result: {'weather_condition': 'Rainy'}")
    print("Orchestrator sees the goal requires related news.")
    print("Dynamically updating Step 2 input based on Step 1 output.")
    updated_search_description = "Search news about Rainy London"
    print(f"Updating Step 2 task description to: '{updated_search_description}'")
    print("Step 2: Executing updated 'search_news' task.")
    # Simulate search result
    final_result_placeholder = {
        "get_weather": {"status": "completed", "output": {"weather_condition": "Rainy"}},
        "search_news": {"status": "completed", "output": {"news_articles": [{"title": "London braces for more rain", "url": "..."}]}}
    }
    print("--- End Orchestrator Internals ---")

    print("\nWorkflow completed (simulation).")
    print("Final Result (Conceptual):")
    import json
    print(json.dumps(final_result_placeholder, indent=2))

# To run this conceptual example:
# asyncio.run(run_dynamic_weather_news_task())

# Note: This example is conceptual. The actual dynamic planning logic resides within the 
# OrchestratorAgent's execution loop and planning phases. The user defines the initial goal, 
# and the orchestrator handles the adaptation based on its internal logic and agent capabilities.
```

## Key Takeaways

* The Orchestrator doesn't just execute static plans.
* It continuously evaluates progress against the overall goal.
* It can modify upcoming steps (change tasks, add inputs) or even insert new steps based on intermediate results.
* This makes the system more robust and capable of handling tasks where the exact steps aren't known upfront.
