from abc import abstractmethod
from typing import List, Dict, Any, Optional

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.ledgers.base import TaskLedger, ProgressLedger

class Orchestrator(Agent):
    """Abstract base class for orchestrator agents.

    Orchestrators are responsible for managing the overall task execution,
    including planning, delegating subtasks to other agents, tracking progress,
    and adapting the plan as needed.
    """

    def __init__(self, name: str, description: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, description or "Manages complex tasks by orchestrating other agents.", config)
        self.agents: Dict[str, Agent] = {} # Dictionary to hold available agents

    def register_agent(self, agent: Agent):
        """Register an agent that the orchestrator can delegate tasks to."""
        if agent.name in self.agents:
            # Handle potential name collision - maybe log a warning or raise error?
            print(f"Warning: Agent with name '{agent.name}' already registered. Overwriting.")
        self.agents[agent.name] = agent
        print(f"Agent '{agent.name}' registered with orchestrator '{self.name}'.")

    def register_agents(self, agents: List[Agent]):
        """Register multiple agents."""
        for agent in agents:
            self.register_agent(agent)

    @abstractmethod
    async def create_initial_plan(self, goal: str, initial_context: Optional[Dict[str, Any]] = None) -> TaskLedger:
        """Creates the initial TaskLedger based on the goal and context."""
        pass

    @abstractmethod
    async def execute_step(self, task_ledger: TaskLedger, progress_ledger: ProgressLedger) -> ProgressLedger:
        """Executes a single step of the plan (Inner Loop logic).

        This typically involves reflection, selecting a subtask/agent, delegation,
        and updating the progress ledger.
        """
        pass

    @abstractmethod
    async def run_task(self, goal: str, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Runs the entire task orchestration from goal to completion or failure.

        This manages both the outer loop (planning/re-planning) and inner loop (step execution).
        """
        pass

    # Overriding execute_task from Agent base class
    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Orchestrator's implementation of execute_task delegates to run_task."""
        # Assuming task_description is the high-level goal for the orchestrator
        return await self.run_task(goal=task_description, initial_context=context) 