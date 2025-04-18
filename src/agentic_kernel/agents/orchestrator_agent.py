"""Orchestrator Agent for managing multi-agent workflows.

This module provides a wrapper around the core OrchestratorAgent implementation
in the orchestrator.core module. It maintains backward compatibility with code
that imports OrchestratorAgent from the agents module.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config_types import AgentConfig
from ..ledgers import PlanStep, ProgressEntry, ProgressLedger, TaskLedger
from ..orchestrator.core import OrchestratorAgent as CoreOrchestratorAgent
from ..types import Task, WorkflowStep
from .base import BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Agent responsible for orchestrating multi-agent workflows.

    This class is a wrapper around the core OrchestratorAgent implementation
    in the orchestrator.core module. It delegates most of its functionality
    to the core implementation while maintaining backward compatibility.
    """

    def __init__(
        self,
        config: AgentConfig,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
    ):
        """Initialize the orchestrator agent.

        Args:
            config: Configuration for the agent
            task_ledger: Ledger for tracking tasks
            progress_ledger: Ledger for tracking workflow progress
        """
        super().__init__(config)

        # Create the core orchestrator agent
        self._core_orchestrator = CoreOrchestratorAgent(
            config=config,
            task_ledger=task_ledger,
            progress_ledger=progress_ledger,
        )

        # Store references to ledgers for backward compatibility
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.available_agents: Dict[str, BaseAgent] = {}

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task by orchestrating a workflow.

        Args:
            task: Task object containing workflow details

        Returns:
            Dictionary containing workflow execution results
        """
        try:
            # Create a workflow step from the task
            workflow_step = WorkflowStep(
                task=task,
                parallel=task.parameters.get("allow_parallel", False)
            )

            # Create a workflow with the step
            workflow_id = await self._core_orchestrator.create_workflow(
                name=f"Task: {task.name}",
                description=task.description or "Task execution workflow",
                steps=[workflow_step],
                creator="orchestrator_agent"
            )

            # Execute the workflow
            result = await self._core_orchestrator.execute_workflow(workflow_id)

            # Map the result to the expected format
            return {
                "status": result.get("status", "error"),
                "output": result.get("output", ""),
                "error": result.get("error", None),
                "metrics": result.get("metrics", {}),
            }
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            return {"status": "error", "error": str(e), "output": "", "metrics": {}}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register
        """
        # Store in local dictionary for backward compatibility
        self.available_agents[agent.__class__.__name__] = agent

        # Delegate to core implementation
        self._core_orchestrator.register_agent(agent)

    async def set_working_directory(self, working_dir: str) -> None:
        """Set the working directory for file operations.

        Args:
            working_dir: Path to the working directory
        """
        logger.info(f"Setting working directory to: {working_dir}")
        # Store the working directory for future use
        self.working_dir = working_dir

        # Propagate to all registered agents that support working directories
        # Use both local agents (for backward compatibility) and core agents
        for agent in self.available_agents.values():
            if hasattr(agent, "set_working_directory"):
                await agent.set_working_directory(working_dir)

        # Also propagate to agents registered with the core orchestrator
        if hasattr(self._core_orchestrator, "agents"):
            for agent in self._core_orchestrator.agents.values():
                if hasattr(agent, "set_working_directory"):
                    await agent.set_working_directory(working_dir)

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics collected during workflow execution.

        Returns:
            Dictionary of metrics
        """
        # If progress_ledger is available, return its metrics (for backward compatibility)
        if hasattr(self, "progress_ledger") and self.progress_ledger and hasattr(self.progress_ledger, "metrics"):
            return self.progress_ledger.metrics

        # Try to get system health metrics from core implementation
        if hasattr(self._core_orchestrator, "get_system_health"):
            system_health = self._core_orchestrator.get_system_health()
            if system_health:
                return system_health

        # Otherwise return basic metrics
        return {
            "registered_agents": len(self.available_agents),
            "timestamp": datetime.now().isoformat(),
        }

    async def execute_workflow(
        self,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
        allow_parallel: bool = False,
    ) -> Dict[str, Any]:
        """Execute a workflow based on the task ledger and progress ledger.

        This method creates a workflow from the task ledger and executes it
        using the core implementation.

        Args:
            task_ledger: Ledger containing the task plan
            progress_ledger: Ledger for tracking progress
            allow_parallel: Whether to allow parallel execution of steps

        Returns:
            Dictionary containing workflow execution results
        """
        try:
            # Create workflow steps from the task ledger plan
            steps = []
            for plan_step in task_ledger.plan:
                # Create a Task object for the step
                task = Task(
                    name=f"Step {plan_step.step_id}",
                    description=plan_step.description,
                    agent_type="auto",  # Let the orchestrator select the agent
                    parameters=plan_step.context or {},
                )

                # Create a WorkflowStep object
                workflow_step = WorkflowStep(
                    task=task,
                    dependencies=plan_step.depends_on,
                    parallel=allow_parallel,
                )

                steps.append(workflow_step)

            # Create a workflow with the steps
            workflow_id = await self._core_orchestrator.create_workflow(
                name=f"Workflow: {task_ledger.goal}",
                description=task_ledger.goal,
                steps=steps,
                creator="orchestrator_agent"
            )

            # Execute the workflow
            result = await self._core_orchestrator.execute_workflow(workflow_id)

            # Update progress ledger
            progress_ledger.current_status = result.get("status", "completed")

            return result

        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            progress_ledger.current_status = "failed"
            return {
                "status": "error",
                "error": str(e),
                "completed_steps": [],
                "retry_count": 0,
                "replanning_events": [],
                "parallel_executions": 0,
                "metrics": {},
                "success_rate": 0.0,
            }

    async def _execute_step(self, step: PlanStep) -> Dict[str, Any]:
        """Execute a single step in the workflow.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        try:
            agent = await self._determine_agent_for_step(step)
            if not agent:
                return {
                    "status": "error",
                    "error": f"No suitable agent found for step {step.step_id}",
                }

            start_time = time.time()
            result = await agent.execute_task(step.description, step.context)
            duration = time.time() - start_time

            # Ensure result is a dictionary
            if not isinstance(result, dict):
                result = {"output": result}

            # Add execution metrics
            metrics = result.get("metrics", {})
            metrics.update(
                {
                    "duration": duration,
                    "cpu_usage": psutil.cpu_percent(),
                    "memory_usage": psutil.Process().memory_info().rss
                    / 1024
                    / 1024,  # MB
                }
            )

            result["metrics"] = metrics
            result["status"] = result.get("status", "success")
            return result

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _determine_agent_for_step(self, step: PlanStep) -> Optional[BaseAgent]:
        """Determine which agent should handle a step based on its description.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        # Simple keyword matching for now
        keywords = {
            "WebSurferAgent": ["research", "documentation", "web", "online"],
            "FileSurferAgent": ["file", "codebase", "analyze", "read"],
            "CoderAgent": ["implement", "code", "generate", "develop"],
            "TerminalAgent": ["execute", "run", "install", "build"],
        }

        max_matches = 0
        best_agent = None

        for agent_name, agent_keywords in keywords.items():
            matches = sum(
                1
                for keyword in agent_keywords
                if keyword.lower() in step.description.lower()
            )
            if matches > max_matches and agent_name in self.available_agents:
                max_matches = matches
                best_agent = self.available_agents[agent_name]

        return best_agent or next(iter(self.available_agents.values()))

    def _get_executable_steps(
        self, plan: List[PlanStep], completed_steps: List[str]
    ) -> List[PlanStep]:
        """Get steps that can be executed based on their dependencies.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        executable = []
        for step in plan:
            if step.status != "completed" and step.step_id not in completed_steps:
                if all(dep in completed_steps for dep in step.depends_on):
                    executable.append(step)
        return executable

    async def _handle_step_failure(
        self, step: PlanStep, error: str, current_retry_count: int
    ) -> Dict[str, Any]:
        """Handle a failed step execution.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        if current_retry_count < self.config["max_task_retries"]:
            # Retry the step
            return {"status": "retry", "retry_count": current_retry_count + 1}

        # Attempt replanning
        new_plan = await self._replan_workflow(
            TaskLedger(
                goal=f"Alternative approach for: {step.description}",
                initial_facts=[f"Previous attempt failed: {error}"],
                assumptions=[],
            ),
            [f"Previous approach failed: {error}"],
        )

        if new_plan:
            return {
                "status": "success",
                "retry_count": current_retry_count,
                "replanned": True,
            }

        return {
            "status": "error",
            "error": f"Step failed after {current_retry_count} retries and replanning attempt",
            "retry_count": current_retry_count,
        }

    async def _evaluate_progress(
        self, task_ledger: TaskLedger, completed_steps: List[str]
    ) -> Dict[str, Any]:
        """Evaluate the current progress and determine if replanning is needed.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        return await self.llm.evaluate_progress(task_ledger, completed_steps)

    async def _replan_workflow(
        self, task_ledger: TaskLedger, suggestions: List[str]
    ) -> Optional[List[PlanStep]]:
        """Replan the workflow based on the current state and suggestions.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.
        """
        try:
            return await self.llm.replan_task(task_ledger, suggestions)
        except Exception as e:
            print(f"Replanning failed: {str(e)}")
            return None

    async def create_initial_plan(
        self, goal: str, initial_context: Optional[Dict[str, Any]] = None
    ) -> TaskLedger:
        """Creates the initial TaskLedger based on the goal and context.

        .. deprecated:: 0.2.0
           This method is deprecated and will be removed in a future version.
           It is kept for backward compatibility.

        Args:
            goal: The high-level goal to achieve
            initial_context: Optional context information for planning

        Returns:
            TaskLedger: A new task ledger with the initial plan
        """
        try:
            # Extract facts and assumptions from context
            facts = initial_context.get("facts", []) if initial_context else []
            assumptions = (
                initial_context.get("assumptions", []) if initial_context else []
            )

            # Create task ledger
            task_ledger = TaskLedger(
                goal=goal, initial_facts=facts, assumptions=assumptions
            )

            # Get available agent capabilities for planning
            agent_capabilities = {
                name: agent.description for name, agent in self.available_agents.items()
            }

            # Create initial plan using LLM
            plan_result = await self.llm.plan_task(
                goal=goal,
                facts=facts,
                assumptions=assumptions,
                available_agents=agent_capabilities,
            )

            # Convert plan to PlanStep objects
            steps = []
            for step_data in plan_result["steps"]:
                step = PlanStep(
                    step_id=str(step_data["id"]),
                    description=step_data["description"],
                    status="pending",
                    depends_on=step_data.get("depends_on", []),
                    context=step_data.get("context", {}),
                    agent_hint=step_data.get("agent"),
                )
                steps.append(step)

            task_ledger.plan = steps
            return task_ledger

        except Exception as e:
            logger.error(f"Error creating initial plan: {str(e)}")
            raise

    async def execute_step(
        self, task_ledger: TaskLedger, progress_ledger: ProgressLedger
    ) -> ProgressLedger:
        """Executes a single step of the plan (Inner Loop logic).

        This method handles:
        1. Reflection on current state
        2. Selecting the next step and agent
        3. Delegating the task
        4. Updating progress

        Args:
            task_ledger: The current task ledger
            progress_ledger: The current progress ledger

        Returns:
            ProgressLedger: Updated progress ledger
        """
        try:
            # Get executable steps
            executable_steps = self._get_executable_steps(
                task_ledger.plan, progress_ledger.completed_steps
            )
            if not executable_steps:
                progress_ledger.current_status = "blocked"
                progress_ledger.add_entry(
                    ProgressEntry(
                        timestamp=datetime.now(),
                        status="blocked",
                        message="No executable steps available",
                    )
                )
                return progress_ledger

            # Select the next step (for now, just take the first executable step)
            current_step = executable_steps[0]

            # Update progress
            progress_ledger.current_status = "executing"
            progress_ledger.add_entry(
                ProgressEntry(
                    timestamp=datetime.now(),
                    status="executing",
                    message=f"Executing step: {current_step.description}",
                )
            )

            # Execute the step
            start_time = time.time()
            result = await self._execute_step(current_step)
            duration = time.time() - start_time

            # Update metrics
            progress_ledger.add_metrics(
                {
                    f"step_{current_step.step_id}_duration": duration,
                    **result.get("metrics", {}),
                }
            )

            # Handle the result
            if result["status"] == "success":
                current_step.status = "completed"
                progress_ledger.completed_steps.append(current_step.step_id)
                progress_ledger.add_entry(
                    ProgressEntry(
                        timestamp=datetime.now(),
                        status="success",
                        message=f"Step {current_step.step_id} completed successfully",
                    )
                )
            else:
                current_step.status = "failed"
                progress_ledger.add_entry(
                    ProgressEntry(
                        timestamp=datetime.now(),
                        status="failed",
                        message=f"Step {current_step.step_id} failed: {result.get('error', 'Unknown error')}",
                    )
                )

                # Handle failure
                retry_result = await self._handle_step_failure(
                    current_step,
                    result.get("error", "Unknown error"),
                    progress_ledger.retry_count,
                )

                if retry_result["status"] == "retry":
                    progress_ledger.retry_count = retry_result["retry_count"]
                    current_step.status = "pending"  # Reset for retry
                elif retry_result.get("replanned"):
                    # Update task ledger with new plan
                    progress_ledger.add_entry(
                        ProgressEntry(
                            timestamp=datetime.now(),
                            status="replanned",
                            message="Step failed, created new plan",
                        )
                    )

            return progress_ledger

        except Exception as e:
            logger.error(f"Error executing step: {str(e)}")
            progress_ledger.add_entry(
                ProgressEntry(
                    timestamp=datetime.now(),
                    status="error",
                    message=f"Error executing step: {str(e)}",
                )
            )
            return progress_ledger

    async def run_task(
        self, goal: str, initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Runs the entire task orchestration from goal to completion or failure.

        This method manages both the outer loop (planning/re-planning) and inner loop
        (step execution). It will:
        1. Create initial plan
        2. Execute steps while monitoring progress
        3. Handle failures and replanning
        4. Track metrics and progress

        Args:
            goal: The high-level goal to achieve
            initial_context: Optional context information

        Returns:
            Dict containing final status, results, and metrics
        """
        try:
            # Create initial plan
            task_ledger = await self.create_initial_plan(goal, initial_context)

            # Initialize progress tracking
            progress_ledger = ProgressLedger(
                task_id=task_ledger.task_id, current_status="planning"
            )
            progress_ledger.add_entry(
                ProgressEntry(
                    timestamp=datetime.now(),
                    status="planning",
                    message="Created initial plan",
                )
            )

            # Main execution loop
            planning_attempts = 0
            while planning_attempts < self.config["max_planning_attempts"]:
                # Execute steps until completion or blocking state
                while progress_ledger.current_status not in [
                    "completed",
                    "failed",
                    "blocked",
                ]:
                    progress_ledger = await self.execute_step(
                        task_ledger, progress_ledger
                    )

                    # Check if all steps are completed
                    if all(step.status == "completed" for step in task_ledger.plan):
                        progress_ledger.current_status = "completed"
                        break

                # If completed or failed, we're done
                if progress_ledger.current_status in ["completed", "failed"]:
                    break

                # If blocked, try replanning
                if progress_ledger.current_status == "blocked":
                    planning_attempts += 1
                    progress_ledger.add_entry(
                        ProgressEntry(
                            timestamp=datetime.now(),
                            status="replanning",
                            message=f"Attempting replan ({planning_attempts}/{self.config['max_planning_attempts']})",
                        )
                    )

                    # Evaluate progress and get suggestions
                    progress = await self._evaluate_progress(
                        task_ledger, progress_ledger.completed_steps
                    )

                    if progress["needs_replanning"]:
                        new_plan = await self._replan_workflow(
                            task_ledger, progress["suggestions"]
                        )
                        if new_plan:
                            task_ledger.plan = new_plan
                            progress_ledger.add_entry(
                                ProgressEntry(
                                    timestamp=datetime.now(),
                                    status="replanned",
                                    message="Created new plan",
                                )
                            )
                            continue

                    # If we can't replan, mark as failed
                    progress_ledger.current_status = "failed"
                    progress_ledger.add_entry(
                        ProgressEntry(
                            timestamp=datetime.now(),
                            status="failed",
                            message="Unable to proceed with execution and replanning failed",
                        )
                    )
                    break

            # Prepare final result
            final_status = (
                "success" if progress_ledger.current_status == "completed" else "error"
            )
            error_msg = None if final_status == "success" else "Task failed to complete"

            return {
                "status": final_status,
                "error": error_msg,
                "completed_steps": progress_ledger.completed_steps,
                "metrics": progress_ledger.metrics,
                "progress_history": [
                    entry.to_dict() for entry in progress_ledger.entries
                ],
                "success_rate": (
                    len(progress_ledger.completed_steps) / len(task_ledger.plan)
                    if task_ledger.plan
                    else 0
                ),
            }

        except Exception as e:
            logger.error(f"Error in task execution: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "completed_steps": [],
                "metrics": {},
                "progress_history": [],
                "success_rate": 0,
            }
