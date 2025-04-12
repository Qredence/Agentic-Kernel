"""Core orchestrator implementation for managing workflow execution."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents import BaseAgent
from ..config import AgentConfig
from ..ledgers import ProgressLedger, TaskLedger
from ..types import Task, WorkflowStep
from .agent_selection import AgentSelector
from .condition_evaluator import ConditionalBranchManager
from .workflow_history import WorkflowHistory
from .workflow_optimizer import WorkflowOptimizer
from .agent_metrics import AgentMetricsCollector

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Agent responsible for orchestrating workflow execution.

    The Orchestrator Agent is responsible for:
    1. Task decomposition and planning
    2. Dynamic plan creation and revision
    3. Task delegation to specialized agents
    4. Progress monitoring and error recovery
    5. Workflow management through nested loops

    Attributes:
        config: Configuration for the orchestrator
        task_ledger: Ledger for tracking tasks
        progress_ledger: Ledger for tracking workflow progress
        agents: Dictionary of registered agents
        agent_selector: Component for intelligently selecting agents for tasks
        workflow_history: Component for tracking workflow versions and execution history
        branch_manager: Component for managing conditional branching in workflows
        workflow_optimizer: Component for optimizing workflows
    """

    def __init__(
        self,
        config: AgentConfig,
        task_ledger: TaskLedger,
        progress_ledger: ProgressLedger,
        history_storage_path: Optional[str] = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Configuration for the orchestrator
            task_ledger: Task tracking ledger
            progress_ledger: Progress tracking ledger
            history_storage_path: Optional path to persist workflow history
        """
        self.config = config
        self.task_ledger = task_ledger
        self.progress_ledger = progress_ledger
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_selector = AgentSelector()
        self.workflow_history = WorkflowHistory()
        self.history_storage_path = history_storage_path
        self.max_planning_attempts = 3
        self.max_inner_loop_iterations = 10
        self.reflection_threshold = 0.7  # Progress threshold before reflection
        self.branch_manager = (
            ConditionalBranchManager()
        )  # Added for conditional branching
        self.workflow_optimizer = WorkflowOptimizer()  # Added for workflow optimization
        self.metrics_collector = AgentMetricsCollector()  # Added for agent performance monitoring

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register
        """
        self.agents[agent.agent_id] = agent
        # Register agent with the metrics collector
        self.metrics_collector.register_agent(agent.agent_id, agent.type)
        logger.info(f"Registered agent: {agent.type} with ID {agent.agent_id}")

    def register_agent_specialization(self, agent_id: str, domains: list[str]) -> None:
        """Register an agent's domain specializations.

        Args:
            agent_id: The ID of the agent
            domains: List of specialized domains
        """
        if agent_id in self.agents:
            self.agent_selector.skill_matrix.register_agent_specialization(
                agent_id, domains
            )
            logger.info(f"Registered specializations for agent {agent_id}: {domains}")
        else:
            logger.warning(
                f"Cannot register specialization for unknown agent: {agent_id}"
            )

    async def _reset_agent_state(self, agent: BaseAgent) -> None:
        """Reset an agent's state.

        Args:
            agent: Agent to reset
        """
        try:
            await agent.reset()
            logger.info(f"Reset state for agent: {agent.type}")
        except Exception as e:
            logger.error(f"Failed to reset agent {agent.type}: {str(e)}")
            raise

    async def select_agent_for_task(
        self, task: Task, context: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseAgent]:
        """Select the best agent for a given task.

        This method uses the agent selector to find the most appropriate
        agent for executing the task based on capabilities and performance.

        Args:
            task: The task to be executed
            context: Optional execution context

        Returns:
            Selected agent instance, or None if no suitable agent found
        """
        # Use the agent selector to find the best agent for this task
        agent_id = await self.agent_selector.select_agent(task, self.agents, context)

        if not agent_id:
            logger.warning(f"No suitable agent found for task: {task.name}")
            return None

        return self.agents.get(agent_id)

    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[WorkflowStep],
        creator: str = "system",
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new workflow and track its initial version.

        Args:
            name: Name of the workflow
            description: Description of the workflow's purpose
            steps: List of workflow steps
            creator: Who created the workflow
            tags: Optional tags for categorizing the workflow

        Returns:
            ID of the created workflow
        """
        # Create workflow in history tracker
        workflow_id, version_id = await self.workflow_history.create_workflow(
            name=name,
            description=description,
            creator=creator,
            steps=steps,
            tags=tags,
        )

        logger.info(f"Created workflow '{name}' with ID {workflow_id}")

        # Persist history if storage path configured
        if self.history_storage_path:
            await self.workflow_history.persist_history(self.history_storage_path)

        return workflow_id

    async def update_workflow(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        description: str,
        creator: str = "system",
    ) -> str:
        """Create a new version of an existing workflow.

        Args:
            workflow_id: ID of the workflow to update
            steps: Updated workflow steps
            description: Description of the changes
            creator: Who created this version

        Returns:
            ID of the new version
        """
        # Create new version in history tracker
        version = await self.workflow_history.create_version(
            workflow_id=workflow_id,
            steps=steps,
            created_by=creator,
            description=description,
        )

        logger.info(
            f"Created new version {version.version_id} for workflow {workflow_id}"
        )

        # Persist history if storage path configured
        if self.history_storage_path:
            await self.workflow_history.persist_history(self.history_storage_path)

        return version.version_id

    async def get_workflow_versions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get the version history for a workflow.

        Args:
            workflow_id: ID of the workflow

        Returns:
            List of version metadata in chronological order
        """
        return await self.workflow_history.get_version_history(workflow_id)

    async def compare_workflow_versions(
        self, workflow_id: str, version_id1: str, version_id2: str
    ) -> Dict[str, Any]:
        """Compare two versions of a workflow.

        Args:
            workflow_id: ID of the workflow
            version_id1: ID of the first version
            version_id2: ID of the second version

        Returns:
            Comparison results detailing differences
        """
        return await self.workflow_history.compare_versions(
            workflow_id, version_id1, version_id2
        )

    async def get_execution_history(
        self, workflow_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get execution history for a workflow.

        Args:
            workflow_id: ID of the workflow
            limit: Maximum number of records to return

        Returns:
            List of execution records in reverse chronological order
        """
        return await self.workflow_history.get_execution_history(workflow_id, limit)

    async def _execute_step(
        self, workflow_id: str, step: WorkflowStep, execution_id: str
    ) -> Dict[str, Any]:
        """Execute a workflow step.

        This method is responsible for:
        1. Selecting the appropriate agent for the task
        2. Executing the task with the selected agent
        3. Recording execution results and metrics
        4. Updating the task ledger with results

        Args:
            workflow_id: ID of the workflow
            step: Workflow step to execute
            execution_id: ID of the current execution

        Returns:
            Dictionary containing execution results
        """
        task = step.task
        start_time = datetime.now()
        logger.info(f"Executing step: {task.name}")

        try:
            # Register the task in the ledger
            await self.task_ledger.register_task(task)

            # Update task status to running
            await self.task_ledger.update_task_status(task.id, "running")

            # Select the best agent for this task
            context = {"workflow_id": workflow_id, "step_name": task.name}
            agent = await self.select_agent_for_task(task, context)

            if not agent:
                raise ValueError(f"No suitable agent found for task: {task.name}")

            # Start tracking task for metrics collection
            task_info = {
                "type": task.type,
                "name": task.name,
                "workflow_id": workflow_id,
                "execution_id": execution_id,
            }
            self.metrics_collector.start_task(agent.agent_id, task.id, task_info)

            # Execute the task with the selected agent
            result = await agent.execute(task)

            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Record execution for future agent selection
            success = result.get("status") == "success"
            self.agent_selector.record_execution_result(
                agent.agent_id, task, success, execution_time
            )

            # Collect metrics for the completed task
            collected_metrics = self.metrics_collector.end_task(agent.agent_id, task.id, result)

            # Update task in ledger
            if success:
                await self.task_ledger.update_task_status(task.id, "completed")
                await self.task_ledger.update_task_output(
                    task.id, result.get("output", {})
                )
            else:
                await self.task_ledger.update_task_status(task.id, "failed")
                await self.task_ledger.update_task_error(
                    task.id, result.get("error", "Unknown error")
                )

            # Add execution metrics
            if "metrics" not in result:
                result["metrics"] = {}
            result["metrics"]["execution_time"] = execution_time
            result["metrics"]["agent_type"] = agent.type
            result["metrics"]["agent_id"] = agent.agent_id

            # Record step result in workflow history
            await self.workflow_history.record_step_result(
                execution_id=execution_id, step_name=task.name, result=result
            )

            # Record step result in branch manager for conditional branching
            self.branch_manager.record_step_result(task.name, result)

            return result

        except Exception as e:
            # Log the error
            logger.error(f"Error executing step {task.name}: {str(e)}")

            # Update task status in ledger
            await self.task_ledger.update_task_status(task.id, "failed")
            await self.task_ledger.update_task_error(task.id, str(e))

            # Record error in workflow history
            error_result = {"status": "failed", "error": str(e)}
            await self.workflow_history.record_step_result(
                execution_id=execution_id, step_name=task.name, result=error_result
            )

            # Record error in branch manager for conditional branching
            self.branch_manager.record_step_result(task.name, error_result)

            # Return error result
            return error_result

    async def execute_workflow(
        self, workflow_id: str, version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            version_id: Optional version ID (uses current version if not specified)

        Returns:
            Dictionary containing workflow execution results
        """
        # Get the workflow version to execute
        version = await self.workflow_history.get_version(workflow_id, version_id)
        if not version:
            error_msg = (
                f"Workflow version not found: {workflow_id}/{version_id or 'current'}"
            )
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        # Start execution record in history
        execution = await self.workflow_history.start_execution(
            workflow_id, version.version_id
        )
        execution_id = execution.execution_id

        # Register workflow with progress ledger
        await self.progress_ledger.register_workflow(execution_id, version.steps)

        # Initialize workflow tracking variables
        completed_steps = []
        failed_steps = []
        retried_steps = []
        skipped_steps = []  # New: track skipped steps due to conditions
        replanned = False
        planning_attempts = 0
        metrics = {
            "execution_time": 0.0,
            "resource_usage": {},
            "success_rate": 0.0,
            "replanning_count": 0,
        }

        # Initialize branch manager with workflow context
        self.branch_manager = ConditionalBranchManager(
            {
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "version_id": version.version_id,
                "start_time": datetime.now().isoformat(),
            }
        )

        start_time = datetime.now()

        try:
            # OUTER LOOP: Manages the task ledger and planning
            while planning_attempts < self.max_planning_attempts:
                planning_attempts += 1

                if planning_attempts > 1:
                    # Re-plan the workflow
                    logger.info(f"Re-planning workflow (attempt {planning_attempts})")
                    metrics["replanning_count"] += 1
                    try:
                        # Get updated steps from replanning
                        updated_steps = await self._replan_workflow(
                            execution_id, version.steps, completed_steps, failed_steps
                        )

                        # Create new version with replanned steps
                        new_version = await self.workflow_history.create_version(
                            workflow_id=workflow_id,
                            steps=updated_steps,
                            created_by="orchestrator",
                            parent_version_id=version.version_id,
                            description=f"Replanned version after execution failure (attempt {planning_attempts})",
                        )

                        # Update current version
                        version = new_version
                        replanned = True

                        # Reset states for all agents
                        for agent in self.agents.values():
                            await self._reset_agent_state(agent)

                    except Exception as e:
                        logger.error(f"Failed to replan workflow: {str(e)}")
                        break

                inner_loop_iterations = 0

                # INNER LOOP: Manages the progress ledger and step execution
                while inner_loop_iterations < self.max_inner_loop_iterations:
                    inner_loop_iterations += 1

                    # Check if workflow is complete by counting steps actually executed or skipped
                    total_handled_steps = (
                        len(completed_steps) + len(failed_steps) + len(skipped_steps)
                    )
                    if total_handled_steps >= len(version.steps):
                        logger.info("Workflow execution completed")
                        break

                    # Check for looping behavior
                    if inner_loop_iterations > len(version.steps) * 2:
                        logger.warning("Possible loop detected in workflow execution")
                        break

                    # Get steps ready for execution from progress ledger
                    progress_ready_steps = await self.progress_ledger.get_ready_steps(
                        execution_id
                    )

                    if not progress_ready_steps:
                        # Check for deadlock
                        remaining = (
                            set(step.task.name for step in version.steps)
                            - set(completed_steps)
                            - set(failed_steps)
                            - set(skipped_steps)
                        )
                        if remaining and not progress_ready_steps:
                            logger.warning(
                                f"Potential deadlock detected. Remaining steps: {remaining}"
                            )
                            break
                        continue

                    # Filter ready steps based on conditions
                    ready_steps = []
                    for step_name in progress_ready_steps:
                        step = next(
                            s for s in version.steps if s.task.name == step_name
                        )

                        # Check if this step should be executed based on its condition
                        if step.condition:
                            should_execute = self.branch_manager.should_execute_step(
                                step_name, step.condition
                            )
                            if not should_execute:
                                # Skip this step due to condition evaluation
                                logger.info(
                                    f"Skipping step {step_name} due to condition evaluation"
                                )
                                skipped_steps.append(step_name)

                                # Update progress ledger to mark the step as skipped
                                await self.progress_ledger.update_step_status(
                                    execution_id, step_name, "skipped"
                                )

                                # Add a placeholder result for this step
                                skip_result = {
                                    "status": "skipped",
                                    "message": "Step skipped due to condition evaluation",
                                }
                                await self.workflow_history.record_step_result(
                                    execution_id=execution_id,
                                    step_name=step_name,
                                    result=skip_result,
                                )
                                self.branch_manager.record_step_result(
                                    step_name, skip_result
                                )
                                continue

                        ready_steps.append(step_name)

                    if not ready_steps:
                        # No steps to execute at this point
                        # This could happen if all ready steps were skipped due to conditions
                        continue

                    # Execute ready steps in sequence (for deterministic execution)
                    for step_name in ready_steps:
                        step = next(
                            s for s in version.steps if s.task.name == step_name
                        )
                        result = await self._execute_step(
                            workflow_id, step, execution_id
                        )

                        # Process result
                        if isinstance(result, Exception) or (
                            isinstance(result, dict)
                            and result.get("status") != "success"
                        ):
                            error_msg = (
                                str(result)
                                if isinstance(result, Exception)
                                else result.get("error", "Unknown error")
                            )
                            logger.error(f"Step {step_name} failed: {error_msg}")
                            failed_steps.append(step_name)
                            await self.progress_ledger.update_step_status(
                                execution_id, step_name, "failed"
                            )

                            # Assess if we need to break the inner loop and replan
                            if await self._should_replan(
                                version.steps, completed_steps, failed_steps
                            ):
                                break
                        else:
                            if result.get("retried", False):
                                retried_steps.append(step_name)
                            completed_steps.append(step_name)
                            await self.progress_ledger.update_step_status(
                                execution_id, step_name, "completed"
                            )

                            # Update metrics
                            step_metrics = result.get("metrics", {})
                            for key, value in step_metrics.items():
                                if key not in metrics["resource_usage"]:
                                    metrics["resource_usage"][key] = 0
                                metrics["resource_usage"][key] += value

                    # Check for progress
                    progress = self._calculate_progress(
                        version.steps, completed_steps, failed_steps, skipped_steps
                    )
                    if (
                        progress < self.reflection_threshold
                        and inner_loop_iterations > 3
                    ):
                        logger.info(
                            f"Insufficient progress ({progress:.2f}). Breaking inner loop to reflect and replan."
                        )
                        break

                # Check if workflow is complete after inner loop (including skipped steps)
                total_handled_steps = (
                    len(completed_steps) + len(failed_steps) + len(skipped_steps)
                )
                if total_handled_steps >= len(version.steps) and len(failed_steps) == 0:
                    logger.info("Workflow execution completed successfully")
                    break

                # Check if no more replanning is needed
                if not await self._should_replan(
                    version.steps, completed_steps, failed_steps
                ):
                    break

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            # Complete execution record in history
            await self.workflow_history.complete_execution(execution_id, "failed")

            # Persist history if storage path configured
            if self.history_storage_path:
                await self.workflow_history.persist_history(self.history_storage_path)

            return {
                "status": "failed",
                "error": str(e),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "replanned": replanned,
                "metrics": metrics,
                "execution_id": execution_id,
            }

        # Calculate final metrics
        end_time = datetime.now()
        metrics["execution_time"] = (end_time - start_time).total_seconds()

        # Calculate success rate considering skipped steps appropriately
        non_skipped_steps = len(version.steps) - len(skipped_steps)
        if non_skipped_steps > 0:
            metrics["success_rate"] = len(completed_steps) / non_skipped_steps
        else:
            metrics["success_rate"] = (
                1.0  # All relevant steps were skipped or succeeded
            )

        # Determine final status
        final_status = "success" if not failed_steps else "partial_success"

        # Complete execution record in history
        await self.workflow_history.complete_execution(execution_id, final_status)

        # Persist history if storage path configured
        if self.history_storage_path:
            await self.workflow_history.persist_history(self.history_storage_path)

        return {
            "status": final_status,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": skipped_steps,
            "retried_steps": retried_steps,
            "replanned": replanned,
            "metrics": metrics,
            "execution_id": execution_id,
        }

    def _calculate_progress(
        self,
        workflow_steps: List[WorkflowStep],
        completed_steps: List[str],
        failed_steps: List[str],
        skipped_steps: Optional[List[str]] = None,
    ) -> float:
        """Calculate workflow progress as a percentage.

        Args:
            workflow_steps: List of all workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names
            skipped_steps: List of skipped step names due to conditions

        Returns:
            Progress percentage (0.0-1.0)
        """
        if not workflow_steps:
            return 1.0

        # Count skipped steps appropriately
        skip_count = len(skipped_steps) if skipped_steps else 0
        total_steps = len(workflow_steps)
        handled_steps = len(completed_steps) + len(failed_steps) + skip_count

        return handled_steps / total_steps

    async def optimize_workflow(
        self, workflow_id: str, version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimize a workflow based on its execution history.

        This method analyzes past executions of the workflow and applies
        optimization strategies to improve performance and resource utilization.

        Args:
            workflow_id: ID of the workflow to optimize
            version_id: Optional specific version to optimize (default: current version)

        Returns:
            Dictionary containing optimization results
        """
        # Get the workflow version to optimize
        version = await self.workflow_history.get_version(workflow_id, version_id)
        if not version:
            error_msg = (
                f"Workflow version not found: {workflow_id}/{version_id or 'current'}"
            )
            logger.error(error_msg)
            return {"status": "failed", "error": error_msg}

        # Get execution history for this workflow
        execution_history = await self.workflow_history.get_execution_history(
            workflow_id
        )

        # Detailed execution data
        detailed_history = []
        for execution in execution_history:
            execution_id = execution.get("execution_id")
            if execution_id:
                details = await self.workflow_history.get_execution_details(
                    execution_id
                )
                if details:
                    detailed_history.append(details)

        if not detailed_history:
            logger.warning(f"No execution history found for workflow {workflow_id}")
            return {
                "status": "no_history",
                "message": "No execution history available for optimization",
            }

        # Apply optimization strategies
        logger.info(
            f"Optimizing workflow {workflow_id} with {len(detailed_history)} execution records"
        )
        (
            optimized_steps,
            optimization_results,
        ) = await self.workflow_optimizer.optimize_workflow(
            workflow_id=workflow_id,
            workflow=version.steps,
            execution_history=detailed_history,
        )

        # Check if any optimizations were applied
        total_changes = optimization_results.get("total_changes", 0)
        if total_changes == 0:
            logger.info(f"No optimizations applied to workflow {workflow_id}")
            return {
                "status": "no_changes",
                "message": "No optimizations were identified for this workflow",
                "details": optimization_results,
            }

        # Create a new optimized version
        new_version = await self.workflow_history.create_version(
            workflow_id=workflow_id,
            steps=optimized_steps,
            created_by="optimizer",
            parent_version_id=version.version_id,
            description=f"Optimized version with {total_changes} improvements",
        )

        # Persist history if storage path configured
        if self.history_storage_path:
            await self.workflow_history.persist_history(self.history_storage_path)

        logger.info(
            f"Created optimized workflow version {new_version.version_id} for {workflow_id}"
        )

        # Return optimization results
        return {
            "status": "success",
            "message": f"Successfully optimized workflow with {total_changes} improvements",
            "version_id": new_version.version_id,
            "details": optimization_results,
        }

    async def compare_optimized_version(
        self, workflow_id: str, original_version_id: str, optimized_version_id: str
    ) -> Dict[str, Any]:
        """Compare original and optimized workflow versions.

        Args:
            workflow_id: ID of the workflow
            original_version_id: ID of the original version
            optimized_version_id: ID of the optimized version

        Returns:
            Dictionary containing comparison results
        """
        # Compare versions using the workflow history
        comparison = await self.workflow_history.compare_versions(
            workflow_id, original_version_id, optimized_version_id
        )

        # Get execution metrics for both versions if available
        original_metrics = await self._get_version_execution_metrics(
            workflow_id, original_version_id
        )
        optimized_metrics = await self._get_version_execution_metrics(
            workflow_id, optimized_version_id
        )

        # Add metrics comparison if both have been executed
        if original_metrics and optimized_metrics:
            metrics_comparison = self._compare_execution_metrics(
                original_metrics, optimized_metrics
            )
            comparison["metrics_comparison"] = metrics_comparison

        return comparison

    async def _get_version_execution_metrics(
        self, workflow_id: str, version_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get average execution metrics for a workflow version.

        Args:
            workflow_id: ID of the workflow
            version_id: ID of the workflow version

        Returns:
            Dictionary of metrics or None if no executions found
        """
        # Get all executions for this workflow
        executions = await self.workflow_history.get_execution_history(workflow_id)

        # Filter executions for this specific version
        version_executions = [
            e
            for e in executions
            if e.get("version_id") == version_id
            and e.get("status") in ["success", "partial_success"]
        ]

        if not version_executions:
            return None

        # Calculate average metrics
        total_time = 0
        total_success_rate = 0

        for execution in version_executions:
            metrics = execution.get("metrics", {})
            total_time += metrics.get("execution_time", 0)
            total_success_rate += metrics.get("success_rate", 0)

        avg_time = total_time / len(version_executions)
        avg_success_rate = total_success_rate / len(version_executions)

        return {
            "avg_execution_time": avg_time,
            "avg_success_rate": avg_success_rate,
            "execution_count": len(version_executions),
        }

    def _compare_execution_metrics(
        self, original_metrics: Dict[str, Any], optimized_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare execution metrics between original and optimized versions.

        Args:
            original_metrics: Metrics for the original version
            optimized_metrics: Metrics for the optimized version

        Returns:
            Dictionary containing metric comparisons
        """
        # Calculate percentage improvements
        time_diff = original_metrics.get(
            "avg_execution_time", 0
        ) - optimized_metrics.get("avg_execution_time", 0)
        time_percent = (
            (time_diff / original_metrics.get("avg_execution_time", 1)) * 100
            if original_metrics.get("avg_execution_time", 0) > 0
            else 0
        )

        success_diff = optimized_metrics.get(
            "avg_success_rate", 0
        ) - original_metrics.get("avg_success_rate", 0)
        success_percent = (
            (success_diff / original_metrics.get("avg_success_rate", 1)) * 100
            if original_metrics.get("avg_success_rate", 0) > 0
            else 0
        )

        return {
            "time_improvement": {
                "absolute": time_diff,
                "percent": time_percent,
                "is_better": time_diff > 0,
            },
            "success_improvement": {
                "absolute": success_diff,
                "percent": success_percent,
                "is_better": success_diff > 0,
            },
            "original_executions": original_metrics.get("execution_count", 0),
            "optimized_executions": optimized_metrics.get("execution_count", 0),
        }

    def get_agent_metrics(
        self, agent_id: str, metric_name: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for a specific agent.

        Args:
            agent_id: ID of the agent to get metrics for
            metric_name: Optional name of a specific metric to retrieve
            limit: Maximum number of metrics to return

        Returns:
            List of metric dictionaries
        """
        if agent_id not in self.agents:
            logger.warning(f"Cannot get metrics for unknown agent: {agent_id}")
            return []

        return self.metrics_collector.get_agent_metrics(agent_id, metric_name, limit)

    def get_agent_metric_summary(
        self, agent_id: str, metric_name: str
    ) -> Dict[str, Any]:
        """Get a statistical summary of a specific metric for an agent.

        Args:
            agent_id: ID of the agent to get metrics for
            metric_name: Name of the metric to summarize

        Returns:
            Dictionary with statistical summary
        """
        if agent_id not in self.agents:
            logger.warning(f"Cannot get metric summary for unknown agent: {agent_id}")
            return {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "median": None,
            }

        return self.metrics_collector.get_agent_metric_summary(agent_id, metric_name)

    def get_all_agent_summaries(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summaries for all registered agents.

        Returns:
            Dictionary mapping agent IDs to their performance summaries
        """
        return self.metrics_collector.get_all_agent_summaries()

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics.

        Returns:
            Dictionary with system health indicators
        """
        return self.metrics_collector.get_system_health()

    def export_agent_metrics(self, format_type: str = "json") -> Dict[str, Any]:
        """Export all agent metrics in a specified format.

        Args:
            format_type: Format to export metrics in (currently only "json" is supported)

        Returns:
            Dictionary with exported metrics data
        """
        return self.metrics_collector.export_metrics(format_type)
