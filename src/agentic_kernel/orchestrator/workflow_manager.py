"""Robust workflow management system for multi-agent workflows.

This module provides a comprehensive workflow management system that integrates
with the dynamic capability registry and provides features for workflow persistence,
resource management, workflow templates, and enhanced error handling.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from ..agents.base import BaseAgent
from ..communication.dynamic_capability_registry import DynamicCapabilityRegistry
from ..types import Task, WorkflowStep
from .agent_metrics import AgentMetricsCollector
from .agent_selection import AgentSelector
from .condition_evaluator import ConditionalBranchManager
from .workflow_history import WorkflowHistory, WorkflowVersion
from .workflow_optimizer import WorkflowOptimizer

logger = logging.getLogger(__name__)


class WorkflowTemplate:
    """Template for creating reusable workflow patterns.

    This class represents a reusable workflow template that can be instantiated
    with different parameters to create concrete workflows.

    Attributes:
        template_id: Unique identifier for the template
        name: Name of the template
        description: Description of the template's purpose
        parameters: Parameters that can be customized when instantiating
        steps: Template steps with parameter placeholders
        created_by: Who created the template
        created_at: When the template was created
        metadata: Additional template metadata
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, dict[str, Any]],
        steps: list[dict[str, Any]],
        created_by: str = "system",
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize a workflow template.

        Args:
            name: Name of the template
            description: Description of the template's purpose
            parameters: Parameters that can be customized when instantiating
            steps: Template steps with parameter placeholders
            created_by: Who created the template
            metadata: Additional template metadata
        """
        self.template_id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.parameters = parameters
        self.steps = steps
        self.created_by = created_by
        self.created_at = datetime.utcnow()
        self.metadata = metadata or {}

    def instantiate(
        self, parameter_values: dict[str, Any], workflow_name: str | None = None,
    ) -> list[WorkflowStep]:
        """Create a concrete workflow from the template.

        Args:
            parameter_values: Values for the template parameters
            workflow_name: Optional name for the workflow (defaults to template name)

        Returns:
            List of instantiated workflow steps
        """
        # Validate parameters
        for param_name, param_spec in self.parameters.items():
            if param_name not in parameter_values and param_spec.get("required", False):
                raise ValueError(f"Required parameter '{param_name}' not provided")

        # Create workflow steps with parameter substitution
        workflow_steps = []

        for step_template in self.steps:
            # Deep copy the step template
            step_dict = json.loads(json.dumps(step_template))

            # Perform parameter substitution
            step_dict = self._substitute_parameters(step_dict, parameter_values)

            # Create task from step dictionary
            task = Task(
                id=step_dict.get("task_id", str(uuid.uuid4())),
                name=step_dict.get("name", ""),
                description=step_dict.get("description", ""),
                agent_type=step_dict.get("agent_type", "any"),
                parameters=step_dict.get("parameters", {}),
                status="pending",
                max_retries=step_dict.get("max_retries", 3),
                timeout=step_dict.get("timeout"),
            )

            # Create workflow step
            workflow_step = WorkflowStep(
                task=task,
                dependencies=step_dict.get("dependencies", []),
                parallel=step_dict.get("parallel", False),
                condition=step_dict.get("condition"),
            )

            workflow_steps.append(workflow_step)

        return workflow_steps

    def _substitute_parameters(
        self, obj: Any, parameter_values: dict[str, Any],
    ) -> Any:
        """Recursively substitute parameters in an object.

        Args:
            obj: Object to perform substitution on
            parameter_values: Values for the template parameters

        Returns:
            Object with parameters substituted
        """
        if isinstance(obj, str):
            # Check for parameter placeholders like ${param_name}
            if obj.startswith("${") and obj.endswith("}"):
                param_name = obj[2:-1]
                if param_name in parameter_values:
                    return parameter_values[param_name]
                if param_name in self.parameters and "default" in self.parameters[param_name]:
                    return self.parameters[param_name]["default"]
                return obj  # Keep as is if no substitution found
            return obj
        if isinstance(obj, list):
            return [self._substitute_parameters(item, parameter_values) for item in obj]
        if isinstance(obj, dict):
            return {k: self._substitute_parameters(v, parameter_values) for k, v in obj.items()}
        return obj


class WorkflowManager:
    """Manages workflow execution and lifecycle.

    This class provides a comprehensive workflow management system that integrates
    with the dynamic capability registry and provides features for workflow persistence,
    resource management, workflow templates, and enhanced error handling.

    Attributes:
        workflow_history: Component for tracking workflow versions and execution history
        capability_registry: Component for dynamic agent discovery
        agent_selector: Component for selecting agents for tasks
        workflow_optimizer: Component for optimizing workflows
        templates: Dictionary of workflow templates
        active_workflows: Dictionary of currently executing workflows
        persistence_path: Path for persisting workflow state
    """

    def __init__(
        self,
        capability_registry: DynamicCapabilityRegistry | None = None,
        persistence_path: str | None = None,
    ):
        """Initialize the workflow manager.

        Args:
            capability_registry: Registry for dynamic agent discovery
            persistence_path: Path for persisting workflow state
        """
        self.workflow_history = WorkflowHistory()
        self.capability_registry = capability_registry
        self.agent_selector = AgentSelector()
        self.workflow_optimizer = WorkflowOptimizer()
        self.templates: dict[str, WorkflowTemplate] = {}
        self.active_workflows: dict[str, dict[str, Any]] = {}
        self.persistence_path = persistence_path
        self.metrics_collector = AgentMetricsCollector()
        self.agents: dict[str, BaseAgent] = {}

        # Create persistence directory if needed
        if persistence_path and not os.path.exists(persistence_path):
            os.makedirs(persistence_path)

    async def register_agent(
        self,
        agent: BaseAgent,
        capabilities: list[dict[str, Any]] | None = None,
        specializations: list[str] | None = None,
    ) -> None:
        """Register an agent with the workflow manager.

        Args:
            agent: Agent to register
            capabilities: Optional list of agent capabilities
            specializations: Optional list of agent specializations
        """
        # Store the agent
        self.agents[agent.agent_id] = agent

        # Register with the agent selector
        await self.agent_selector.skill_matrix.register_agent_capabilities(agent)

        # Register specializations if provided
        if specializations:
            self.agent_selector.skill_matrix.register_agent_specialization(
                agent.agent_id, specializations,
            )

        # Register with the capability registry if available
        if self.capability_registry:
            await self.capability_registry.register_agent(
                agent_id=agent.agent_id,
                agent_type=agent.type,
                capabilities=capabilities,
                status="active",
                resources=agent.get_resources(),
                metadata=agent.get_metadata(),
            )

        # Register with the metrics collector
        self.metrics_collector.register_agent(agent.agent_id, agent.type)

        logger.info(f"Registered agent: {agent.type} with ID {agent.agent_id}")

    async def discover_agents(
        self, capability_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Discover agents with specific capabilities.

        Args:
            capability_types: Types of capabilities to look for

        Returns:
            List of discovered agents
        """
        if not self.capability_registry:
            logger.warning("Cannot discover agents: no capability registry available")
            return []

        # Use the capability registry to discover agents
        discovered = await self.capability_registry.discover_capabilities(
            requester_id="workflow_manager",
            capability_types=capability_types,
            detail_level="detailed",
        )

        logger.info(f"Discovered {len(discovered)} agents with matching capabilities")
        return discovered

    async def register_workflow_template(
        self, template: WorkflowTemplate,
    ) -> str:
        """Register a workflow template.

        Args:
            template: The workflow template to register

        Returns:
            The template ID
        """
        self.templates[template.template_id] = template
        logger.info(f"Registered workflow template: {template.name} ({template.template_id})")

        # Persist templates if path is configured
        if self.persistence_path:
            await self._persist_templates()

        return template.template_id

    async def create_workflow_from_template(
        self,
        template_id: str,
        parameter_values: dict[str, Any],
        workflow_name: str | None = None,
        description: str | None = None,
        creator: str = "system",
        tags: list[str] | None = None,
    ) -> str | None:
        """Create a workflow from a template.

        Args:
            template_id: ID of the template to use
            parameter_values: Values for the template parameters
            workflow_name: Optional name for the workflow
            description: Optional description for the workflow
            creator: Who is creating the workflow
            tags: Optional tags for the workflow

        Returns:
            ID of the created workflow, or None if template not found
        """
        # Get the template
        if template_id not in self.templates:
            logger.error(f"Template not found: {template_id}")
            return None

        template = self.templates[template_id]

        try:
            # Instantiate the template
            workflow_steps = template.instantiate(
                parameter_values, workflow_name,
            )

            # Create the workflow
            workflow_id, _ = await self.workflow_history.create_workflow(
                name=workflow_name or template.name,
                description=description or template.description,
                creator=creator,
                steps=workflow_steps,
                tags=tags,
            )

            logger.info(f"Created workflow {workflow_id} from template {template_id}")
            return workflow_id

        except Exception as e:
            logger.error(f"Error creating workflow from template: {str(e)}")
            return None

    async def execute_workflow(
        self,
        workflow_id: str,
        version_id: str | None = None,
        execution_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            version_id: Optional version ID (uses current version if not specified)
            execution_timeout: Optional timeout for workflow execution

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

        try:
            # Start execution record in history
            execution = await self.workflow_history.start_execution(
                workflow_id, version.version_id,
            )
            execution_id = execution.execution_id

            # Initialize workflow tracking variables
            completed_steps = []
            failed_steps = []
            skipped_steps = []
            retried_steps = []
            metrics = {
                "execution_time": 0.0,
                "resource_usage": {},
                "success_rate": 0.0,
                "replanning_count": 0,
            }

            # Initialize branch manager with workflow context
            branch_manager = ConditionalBranchManager(
                {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "version_id": version.version_id,
                    "start_time": datetime.now().isoformat(),
                },
            )

            # Track active workflow
            self.active_workflows[execution_id] = {
                "workflow_id": workflow_id,
                "version_id": version.version_id,
                "start_time": datetime.now(),
                "status": "running",
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
            }

            # Persist active workflow state
            await self._persist_workflow_state(execution_id)

            start_time = datetime.now()

            # Set up execution timeout if specified
            if execution_timeout:
                execution_task = asyncio.create_task(
                    self._execute_workflow_steps(
                        workflow_id,
                        version,
                        execution_id,
                        branch_manager,
                        completed_steps,
                        failed_steps,
                        skipped_steps,
                        retried_steps,
                        metrics,
                    ),
                )

                try:
                    result = await asyncio.wait_for(execution_task, timeout=execution_timeout)
                except asyncio.TimeoutError:
                    logger.error(f"Workflow execution timed out after {execution_timeout} seconds")
                    result = {
                        "status": "timeout",
                        "error": f"Execution timed out after {execution_timeout} seconds",
                        "completed_steps": completed_steps,
                        "failed_steps": failed_steps,
                        "skipped_steps": skipped_steps,
                        "retried_steps": retried_steps,
                        "metrics": metrics,
                        "execution_id": execution_id,
                    }
            else:
                # Execute workflow without timeout
                result = await self._execute_workflow_steps(
                    workflow_id,
                    version,
                    execution_id,
                    branch_manager,
                    completed_steps,
                    failed_steps,
                    skipped_steps,
                    retried_steps,
                    metrics,
                )

            # Calculate final metrics
            end_time = datetime.now()
            metrics["execution_time"] = (end_time - start_time).total_seconds()

            # Calculate success rate considering skipped steps appropriately
            non_skipped_steps = len(version.steps) - len(skipped_steps)
            if non_skipped_steps > 0:
                metrics["success_rate"] = len(completed_steps) / non_skipped_steps
            else:
                metrics["success_rate"] = 1.0  # All relevant steps were skipped or succeeded

            # Determine final status
            final_status = "success" if not failed_steps else "partial_success"

            # Complete execution record in history
            await self.workflow_history.complete_execution(execution_id, final_status)

            # Remove from active workflows
            if execution_id in self.active_workflows:
                del self.active_workflows[execution_id]

            # Persist workflow history
            if self.persistence_path:
                await self._persist_workflow_history()

            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")

            # Complete execution record in history
            await self.workflow_history.complete_execution(execution_id, "failed")

            return {
                "status": "failed",
                "error": str(e),
                "execution_id": execution_id,
            }

    async def _execute_workflow_steps(
        self,
        workflow_id: str,
        version: WorkflowVersion,
        execution_id: str,
        branch_manager: ConditionalBranchManager,
        completed_steps: list[str],
        failed_steps: list[str],
        skipped_steps: list[str],
        retried_steps: list[str],
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the steps of a workflow.

        Args:
            workflow_id: ID of the workflow
            version: Workflow version to execute
            execution_id: ID of the current execution
            branch_manager: Manager for conditional branching
            completed_steps: List to track completed steps
            failed_steps: List to track failed steps
            skipped_steps: List to track skipped steps
            retried_steps: List to track retried steps
            metrics: Dictionary to track execution metrics

        Returns:
            Dictionary containing workflow execution results
        """
        # Maximum number of planning attempts and inner loop iterations
        max_planning_attempts = 3
        max_inner_loop_iterations = 10
        reflection_threshold = 0.7  # Progress threshold before reflection

        planning_attempts = 0
        replanned = False

        try:
            # OUTER LOOP: Manages planning and replanning
            while planning_attempts < max_planning_attempts:
                planning_attempts += 1

                if planning_attempts > 1:
                    # Re-plan the workflow
                    logger.info(f"Re-planning workflow (attempt {planning_attempts})")
                    metrics["replanning_count"] += 1
                    try:
                        # Get updated steps from replanning
                        updated_steps = await self._replan_workflow(
                            workflow_id, version.steps, completed_steps, failed_steps,
                        )

                        # Create new version with replanned steps
                        new_version = await self.workflow_history.create_version(
                            workflow_id=workflow_id,
                            steps=updated_steps,
                            created_by="workflow_manager",
                            parent_version_id=version.version_id,
                            description=f"Replanned version after execution failure (attempt {planning_attempts})",
                        )

                        # Update current version
                        version = new_version
                        replanned = True

                    except Exception as e:
                        logger.error(f"Failed to replan workflow: {str(e)}")
                        break

                inner_loop_iterations = 0

                # INNER LOOP: Manages step execution
                while inner_loop_iterations < max_inner_loop_iterations:
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

                    # Get steps ready for execution
                    ready_steps = await self._get_ready_steps(
                        version.steps, completed_steps, failed_steps, skipped_steps,
                    )

                    if not ready_steps:
                        # Check for deadlock
                        remaining = (
                            set(step.task.name for step in version.steps)
                            - set(completed_steps)
                            - set(failed_steps)
                            - set(skipped_steps)
                        )
                        if remaining and not ready_steps:
                            logger.warning(
                                f"Potential deadlock detected. Remaining steps: {remaining}",
                            )
                            break
                        await asyncio.sleep(0.1)
                        continue

                    # Execute ready steps
                    for step_name in ready_steps:
                        step = next(
                            s for s in version.steps if s.task.name == step_name
                        )

                        # Check if this step should be executed based on its condition
                        if step.condition:
                            should_execute = branch_manager.should_execute_step(
                                step_name, step.condition,
                            )
                            if not should_execute:
                                # Skip this step due to condition evaluation
                                logger.info(
                                    f"Skipping step {step_name} due to condition evaluation",
                                )
                                skipped_steps.append(step_name)
                                continue

                        # Execute the step
                        result = await self._execute_step(
                            workflow_id, step, execution_id, branch_manager,
                        )

                        # Process result
                        if result.get("status") == "success":
                            completed_steps.append(step_name)
                        else:
                            failed_steps.append(step_name)

                            # Check if we need to replan
                            if self._should_replan(version.steps, completed_steps, failed_steps):
                                break

                    # Check for progress
                    progress = self._calculate_progress(
                        version.steps, completed_steps, failed_steps, skipped_steps,
                    )
                    if progress < reflection_threshold and inner_loop_iterations > 3:
                        logger.info(
                            f"Insufficient progress ({progress:.2f}). Breaking inner loop to reflect and replan.",
                        )
                        break

                # Check if workflow is complete after inner loop
                total_handled_steps = (
                    len(completed_steps) + len(failed_steps) + len(skipped_steps)
                )
                if total_handled_steps >= len(version.steps) and len(failed_steps) == 0:
                    logger.info("Workflow execution completed successfully")
                    break

                # Check if no more replanning is needed
                if not self._should_replan(version.steps, completed_steps, failed_steps):
                    break

            # Return final result
            return {
                "status": "success" if not failed_steps else "partial_success",
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "retried_steps": retried_steps,
                "replanned": replanned,
                "metrics": metrics,
                "execution_id": execution_id,
            }

        except Exception as e:
            logger.error(f"Error executing workflow steps: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "skipped_steps": skipped_steps,
                "retried_steps": retried_steps,
                "metrics": metrics,
                "execution_id": execution_id,
            }

    async def _execute_step(
        self,
        workflow_id: str,
        step: WorkflowStep,
        execution_id: str,
        branch_manager: ConditionalBranchManager,
    ) -> dict[str, Any]:
        """Execute a workflow step.

        Args:
            workflow_id: ID of the workflow
            step: Workflow step to execute
            execution_id: ID of the current execution
            branch_manager: Manager for conditional branching

        Returns:
            Dictionary containing execution results
        """
        task = step.task
        start_time = datetime.now()
        logger.info(f"Executing step: {task.name}")

        try:
            # Select the best agent for this task
            context = {"workflow_id": workflow_id, "step_name": task.name}
            agent_id = await self.agent_selector.select_agent(
                task, self.agents, context,
            )

            if not agent_id:
                raise ValueError(f"No suitable agent found for task: {task.name}")

            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Selected agent {agent_id} not found")

            # Start tracking task for metrics collection
            task_info = {
                "type": task.type,
                "name": task.name,
                "workflow_id": workflow_id,
                "execution_id": execution_id,
            }
            self.metrics_collector.start_task(agent_id, task.id, task_info)

            # Execute the task with the selected agent
            result = await agent.execute(task)

            # Calculate execution time
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Record execution for future agent selection
            success = result.get("status") == "success"
            self.agent_selector.record_execution_result(
                agent_id, task, success, execution_time,
            )

            # Collect metrics for the completed task
            collected_metrics = self.metrics_collector.end_task(agent_id, task.id, result)

            # Add execution metrics
            if "metrics" not in result:
                result["metrics"] = {}
            result["metrics"]["execution_time"] = execution_time
            result["metrics"]["agent_type"] = agent.type
            result["metrics"]["agent_id"] = agent_id

            # Record step result in workflow history
            await self.workflow_history.record_step_result(
                execution_id=execution_id, step_name=task.name, result=result,
            )

            # Record step result in branch manager for conditional branching
            branch_manager.record_step_result(task.name, result)

            return result

        except Exception as e:
            # Log the error
            logger.error(f"Error executing step {task.name}: {str(e)}")

            # Record error in workflow history
            error_result = {"status": "failed", "error": str(e)}
            await self.workflow_history.record_step_result(
                execution_id=execution_id, step_name=task.name, result=error_result,
            )

            # Record error in branch manager for conditional branching
            branch_manager.record_step_result(task.name, error_result)

            # Return error result
            return error_result

    async def _get_ready_steps(
        self,
        workflow_steps: list[WorkflowStep],
        completed_steps: list[str],
        failed_steps: list[str],
        skipped_steps: list[str],
    ) -> list[str]:
        """Get steps that are ready for execution.

        Args:
            workflow_steps: List of all workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names
            skipped_steps: List of skipped step names

        Returns:
            List of step names that are ready for execution
        """
        ready_steps = []

        for step in workflow_steps:
            step_name = step.task.name

            # Skip steps that are already completed, failed, or skipped
            if (
                step_name in completed_steps
                or step_name in failed_steps
                or step_name in skipped_steps
            ):
                continue

            # Check if all dependencies are satisfied
            dependencies_satisfied = True
            for dep in step.dependencies:
                if dep not in completed_steps and dep not in skipped_steps:
                    dependencies_satisfied = False
                    break

            if dependencies_satisfied:
                ready_steps.append(step_name)

        return ready_steps

    def _should_replan(
        self,
        workflow_steps: list[WorkflowStep],
        completed_steps: list[str],
        failed_steps: list[str],
    ) -> bool:
        """Determine if workflow replanning is needed.

        Args:
            workflow_steps: List of workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names

        Returns:
            True if replanning is needed, False otherwise
        """
        # If no failures, no need to replan
        if not failed_steps:
            return False

        # If all steps are either completed or failed, no point in replanning
        if len(completed_steps) + len(failed_steps) >= len(workflow_steps):
            return False

        # If critical steps have failed, we should replan
        critical_failures = any(
            step.task.critical for step in workflow_steps if step.task.name in failed_steps
        )
        if critical_failures:
            logger.info("Critical step failures detected, replanning needed")
            return True

        # If too many failures relative to progress, we should replan
        failure_ratio = len(failed_steps) / len(workflow_steps)
        if failure_ratio > 0.3:  # More than 30% failures
            logger.info(f"High failure ratio ({failure_ratio:.2f}), replanning needed")
            return True

        return False

    def _calculate_progress(
        self,
        workflow_steps: list[WorkflowStep],
        completed_steps: list[str],
        failed_steps: list[str],
        skipped_steps: list[str],
    ) -> float:
        """Calculate workflow progress as a percentage.

        Args:
            workflow_steps: List of all workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names
            skipped_steps: List of skipped step names

        Returns:
            Progress percentage (0.0-1.0)
        """
        if not workflow_steps:
            return 1.0

        # Count skipped steps appropriately
        total_steps = len(workflow_steps)
        handled_steps = len(completed_steps) + len(failed_steps) + len(skipped_steps)

        return handled_steps / total_steps

    async def _replan_workflow(
        self,
        workflow_id: str,
        original_steps: list[WorkflowStep],
        completed_steps: list[str],
        failed_steps: list[str],
    ) -> list[WorkflowStep]:
        """Replan a workflow based on execution results.

        Args:
            workflow_id: ID of the workflow
            original_steps: Original workflow steps
            completed_steps: List of completed step names
            failed_steps: List of failed step names

        Returns:
            List of replanned workflow steps
        """
        logger.info(f"Replanning workflow {workflow_id}")

        # Create a copy of the original steps to modify
        replanned_steps = []

        # Keep track of steps that need to be replaced or modified
        steps_to_replace = set(failed_steps)

        # First pass: identify dependencies that need to be updated
        dependency_map = {}
        for step in original_steps:
            step_name = step.task.name
            dependency_map[step_name] = set(step.dependencies)

        # Identify steps that depend on failed steps (indirect dependencies)
        affected_steps = set(failed_steps)
        changed = True
        while changed:
            changed = False
            for step_name, deps in dependency_map.items():
                if step_name not in affected_steps and deps.intersection(affected_steps):
                    affected_steps.add(step_name)
                    changed = True

        # Remove completed steps from affected steps
        affected_steps = affected_steps - set(completed_steps)

        # Use the workflow optimizer to generate alternative steps
        try:
            # Get the workflow context
            workflow_info = await self.workflow_history.get_workflow(workflow_id)

            # Create context for optimization
            optimization_context = {
                "workflow_id": workflow_id,
                "workflow_name": workflow_info.name,
                "workflow_description": workflow_info.description,
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "affected_steps": list(affected_steps),
                "available_agents": list(self.agents.keys()),
            }

            # Get alternative steps from the optimizer
            alternative_steps = await self.workflow_optimizer.generate_alternatives(
                original_steps=original_steps,
                failed_steps=list(failed_steps),
                affected_steps=list(affected_steps),
                context=optimization_context,
            )

            # Second pass: build the replanned workflow
            for step in original_steps:
                step_name = step.task.name

                if step_name in completed_steps:
                    # Keep completed steps as-is
                    replanned_steps.append(step)
                elif step_name in affected_steps:
                    # Replace affected steps with alternatives
                    if step_name in alternative_steps:
                        replanned_steps.append(alternative_steps[step_name])
                    else:
                        # If no alternative is available, modify the original step
                        modified_step = self._modify_step_for_retry(step)
                        replanned_steps.append(modified_step)
                else:
                    # Keep unaffected steps as-is
                    replanned_steps.append(step)

            # Ensure all dependencies are still valid
            replanned_steps = self._validate_and_fix_dependencies(
                replanned_steps, completed_steps,
            )

            logger.info(f"Successfully replanned workflow with {len(replanned_steps)} steps")
            return replanned_steps

        except Exception as e:
            logger.error(f"Error during workflow replanning: {str(e)}")

            # Fallback: simple retry strategy for failed steps
            for step in original_steps:
                step_name = step.task.name

                if step_name in completed_steps:
                    # Keep completed steps as-is
                    replanned_steps.append(step)
                elif step_name in failed_steps:
                    # Modify failed steps for retry
                    modified_step = self._modify_step_for_retry(step)
                    replanned_steps.append(modified_step)
                else:
                    # Keep other steps as-is
                    replanned_steps.append(step)

            logger.info(f"Used fallback replanning with {len(replanned_steps)} steps")
            return replanned_steps

    def _modify_step_for_retry(self, step: WorkflowStep) -> WorkflowStep:
        """Modify a step for retry after failure.

        Args:
            step: The original workflow step

        Returns:
            Modified workflow step for retry
        """
        # Create a copy of the task with increased retry count
        task_dict = step.task.to_dict()
        task_dict["id"] = f"{task_dict['id']}_retry_{uuid.uuid4().hex[:8]}"
        task_dict["max_retries"] = task_dict.get("max_retries", 3) + 1
        task_dict["status"] = "pending"

        # Add retry information to parameters
        if "parameters" not in task_dict:
            task_dict["parameters"] = {}
        task_dict["parameters"]["is_retry"] = True
        task_dict["parameters"]["original_task_id"] = step.task.id

        # Create new task and step
        new_task = Task(**task_dict)
        new_step = WorkflowStep(
            task=new_task,
            dependencies=step.dependencies,
            parallel=step.parallel,
            condition=step.condition,
        )

        return new_step

    def _validate_and_fix_dependencies(
        self, steps: list[WorkflowStep], completed_steps: list[str],
    ) -> list[WorkflowStep]:
        """Validate and fix dependencies in replanned steps.

        Args:
            steps: List of workflow steps
            completed_steps: List of completed step names

        Returns:
            List of workflow steps with valid dependencies
        """
        # Create a map of step names
        step_names = {step.task.name for step in steps}
        step_names.update(completed_steps)

        # Fix dependencies
        fixed_steps = []
        for step in steps:
            # Filter out dependencies that no longer exist
            valid_dependencies = [
                dep for dep in step.dependencies if dep in step_names
            ]

            # Create a new step with valid dependencies
            new_step = WorkflowStep(
                task=step.task,
                dependencies=valid_dependencies,
                parallel=step.parallel,
                condition=step.condition,
            )

            fixed_steps.append(new_step)

        return fixed_steps

    async def _persist_templates(self) -> None:
        """Persist workflow templates to disk."""
        if not self.persistence_path:
            return

        templates_path = os.path.join(self.persistence_path, "templates.json")

        try:
            # Convert templates to serializable format
            serialized_templates = {}
            for template_id, template in self.templates.items():
                serialized_templates[template_id] = {
                    "template_id": template.template_id,
                    "name": template.name,
                    "description": template.description,
                    "parameters": template.parameters,
                    "steps": template.steps,
                    "created_by": template.created_by,
                    "created_at": template.created_at.isoformat(),
                    "metadata": template.metadata,
                }

            # Write to file
            with open(templates_path, "w") as f:
                json.dump(serialized_templates, f, indent=2)

            logger.debug(f"Persisted {len(serialized_templates)} templates to {templates_path}")

        except Exception as e:
            logger.error(f"Error persisting templates: {str(e)}")

    async def _persist_workflow_state(self, execution_id: str) -> None:
        """Persist workflow state to disk.

        Args:
            execution_id: ID of the workflow execution
        """
        if not self.persistence_path:
            return

        state_path = os.path.join(self.persistence_path, f"execution_{execution_id}.json")

        try:
            # Get workflow state
            workflow_state = self.active_workflows.get(execution_id)
            if not workflow_state:
                return

            # Convert to serializable format
            serialized_state = dict(workflow_state)
            serialized_state["start_time"] = serialized_state["start_time"].isoformat()

            # Write to file
            with open(state_path, "w") as f:
                json.dump(serialized_state, f, indent=2)

            logger.debug(f"Persisted workflow state for execution {execution_id}")

        except Exception as e:
            logger.error(f"Error persisting workflow state: {str(e)}")

    async def _persist_workflow_history(self) -> None:
        """Persist workflow history to disk."""
        if not self.persistence_path:
            return

        history_path = os.path.join(self.persistence_path, "workflow_history.json")

        try:
            # Get serializable history
            serialized_history = await self.workflow_history.to_dict()

            # Write to file
            with open(history_path, "w") as f:
                json.dump(serialized_history, f, indent=2)

            logger.debug(f"Persisted workflow history to {history_path}")

        except Exception as e:
            logger.error(f"Error persisting workflow history: {str(e)}")

    async def load_persisted_state(self) -> None:
        """Load persisted state from disk."""
        if not self.persistence_path or not os.path.exists(self.persistence_path):
            return

        # Load templates
        templates_path = os.path.join(self.persistence_path, "templates.json")
        if os.path.exists(templates_path):
            try:
                with open(templates_path) as f:
                    serialized_templates = json.load(f)

                for template_data in serialized_templates.values():
                    template = WorkflowTemplate(
                        name=template_data["name"],
                        description=template_data["description"],
                        parameters=template_data["parameters"],
                        steps=template_data["steps"],
                        created_by=template_data["created_by"],
                        metadata=template_data["metadata"],
                    )
                    template.template_id = template_data["template_id"]
                    template.created_at = datetime.fromisoformat(template_data["created_at"])

                    self.templates[template.template_id] = template

                logger.info(f"Loaded {len(self.templates)} templates from {templates_path}")

            except Exception as e:
                logger.error(f"Error loading templates: {str(e)}")

        # Load workflow history
        history_path = os.path.join(self.persistence_path, "workflow_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path) as f:
                    serialized_history = json.load(f)

                await self.workflow_history.from_dict(serialized_history)

                logger.info(f"Loaded workflow history from {history_path}")

            except Exception as e:
                logger.error(f"Error loading workflow history: {str(e)}")
