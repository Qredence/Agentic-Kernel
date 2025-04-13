# Example: Memory System Usage in Workflows

The Agentic Kernel includes a memory system that allows agents to store and retrieve information across tasks and even across different workflow executions (if persistence is configured). This enables agents to learn, recall context, and build upon previous knowledge.

## Scenario

Let's demonstrate a simple memory interaction within a workflow:

1. **Research:** An agent searches the web for a specific topic (e.g., "benefits of microservices architecture").
2. **Memorize:** The agent stores the key findings or a summary of the search results into its memory, associating it with the topic.
3. **Recall:** Later (potentially in a different workflow or a subsequent step), an agent needs information on that topic and queries the memory system to retrieve the previously stored findings.

## Required Components

* `WebSearchAgent`: Performs web searches.
* `MemoryAgent`: An agent (or capability within other agents) that interacts with the memory system (e.g., `MemoryManager`). Needs methods like `add_memory` and `search_memory`.
* `OrchestratorAgent`: Manages the workflow and implicit agent interactions with memory.

## Plan: Incorporating Memory Steps

1. **Step 1: Search Web**
    * Agent: `WebSearchAgent`
    * Task: Search for "benefits of microservices architecture".
    * Outputs: `search_results` (e.g., list of snippets or URLs).
2. **Step 2: Add Findings to Memory**
    * Agent: `MemoryAgent`
    * Task: Store the `search_results` in memory.
    * Inputs: `search_results` from Step 1, `topic` = "microservices benefits".
    * (This step might not have a significant output needed by subsequent steps, but confirms memory addition).
3. **Step 3: (Later/Separate Task) Recall from Memory**
    * Agent: `MemoryAgent`
    * Task: Retrieve information about "microservices benefits".
    * Inputs: `query` = "microservices benefits".
    * Outputs: `retrieved_memories`.

## Conceptual Code Example

```python
import asyncio
from agentic_kernel.types import Task, Workflow, WorkflowStep
from agentic_kernel.orchestrator.core import OrchestratorAgent # Assuming OrchestratorAgent
# Assume MemoryManager is available/accessible, perhaps via the orchestrator or agent context
# from agentic_kernel.memory import MemoryManager 

# Assume agents are registered
# orchestrator = OrchestratorAgent(...)
# search_agent = WebSearchAgent()
# memory_agent = MemoryAgent(memory_manager=...) # Agent needs access to memory manager
# orchestrator.register_agent(search_agent)
# orchestrator.register_agent(memory_agent)

async def run_memory_workflow_part1():
    # Part 1: Search and Memorize
    goal = "Research microservices benefits and store the findings."
    topic = "microservices benefits"

    steps = [
        WorkflowStep(
            step_id="search_web",
            task=Task(
                description=f"Search web for '{topic}'",
                agent_id="WebSearchAgent",
                inputs={"query": topic}
            ),
            outputs={"web_results": "search_results_data"}
        ),
        WorkflowStep(
            step_id="add_to_memory",
            task=Task(
                description="Store search findings in memory",
                agent_id="MemoryAgent", # Agent capable of memory operations
                inputs={
                    "content_to_store": "search_results_data", 
                    "memory_topic": topic,
                    "memory_type": "research_finding" # Optional categorization
                }
            ),
            # This step might output a confirmation ID, omitted for simplicity
            outputs={}
        ),
    ]

    workflow = Workflow(
        workflow_id="research_and_memorize",
        description=goal,
        steps=steps
    )

    print(f"Starting Workflow Part 1: {goal}")
    # result = await orchestrator.execute_workflow(workflow)

    print("\n--- Orchestrator Internals (Conceptual) ---")
    print("Step 1 'search_web': Executing...")
    step1_output = {"search_results_data": ["Scalability", "Indep. Deployment", "Tech Diversity"]}
    print(f"-> Result: {step1_output}")

    print("\nStep 2 'add_to_memory': Executing...")
    print(f"-> Input: {{'content_to_store': {step1_output['search_results_data']}, 'memory_topic': '{topic}'}}")
    # MemoryAgent interacts with MemoryManager
    print("-> MemoryAgent: Adding content to memory under topic '{topic}'.")
    step2_output = {"memory_add_status": "success"}
    print(f"-> Result: {step2_output}")
    print("--- End Orchestrator Internals ---")

    print("\nWorkflow Part 1 completed.")

async def run_memory_workflow_part2():
    # Part 2: Recall from Memory
    goal = "Retrieve stored information about microservices benefits."
    query = "microservices benefits"

    steps = [
        WorkflowStep(
            step_id="search_memory",
            task=Task(
                description=f"Search memory for '{query}'",
                agent_id="MemoryAgent",
                inputs={"query": query, "max_results": 1}
            ),
            outputs={"retrieved_content": "remembered_data"}
        ),
        # ... potentially other steps using the remembered_data ...
    ]

    workflow = Workflow(
        workflow_id="recall_from_memory",
        description=goal,
        steps=steps
    )

    print(f"\nStarting Workflow Part 2: {goal}")
    # result = await orchestrator.execute_workflow(workflow)

    print("\n--- Orchestrator Internals (Conceptual) ---")
    print("Step 1 'search_memory': Executing...")
    print(f"-> Input: {{'query': '{query}'}}")
    # MemoryAgent interacts with MemoryManager
    print(f"-> MemoryAgent: Searching memory for '{query}'.")
    # Simulate finding the previously stored memory
    step1_output = {"retrieved_content": [{"content": ["Scalability", "Indep. Deployment", "Tech Diversity"], "metadata": {"topic": "microservices benefits", "additional_metadata": "..."}}]}
    print(f"-> Result: {step1_output}")
    print("--- End Orchestrator Internals ---")

    print("\nWorkflow Part 2 completed.")
    print(f"Retrieved Data (Conceptual): {step1_output['retrieved_content']}")

# To run this conceptual example:
# asyncio.run(run_memory_workflow_part1())
# asyncio.run(run_memory_workflow_part2())

# Note: This example splits the process into two parts for clarity. In a real scenario,
# memory recall could happen in a later step of the same workflow or a completely 
# separate workflow execution, relying on the persistence of the MemoryManager.
```

## Key Takeaways

* Agents can be designed to interact with a central `MemoryManager`.
* Workflows can include steps specifically for adding information to memory, often taking input from previous steps.
* Other steps (or separate workflows) can query the memory using relevant search terms.
* The memory system uses techniques like semantic search (vector embeddings) to find relevant memories even if the query doesn't exactly match the stored text.
* This allows agents to build up knowledge over time and leverage past findings.
