"""Orchestrator agent for coordinating workflows in the Agentic-Kernel system.

This module implements the orchestrator agent responsible for:
1. Managing workflow execution
2. Task delegation to appropriate agents
3. Progress monitoring and status updates
4. Error handling and recovery
5. Inter-agent communication coordination
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from .agents.base import BaseAgent
from .communication.message import Message, MessagePriority, MessageType
from .communication.protocol import CommunicationProtocol, MessageBus
from .config import AgentConfig
from .exceptions import TaskExecutionError, WorkflowError
from .types import Task, TaskStatus, Workflow

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Agent responsible for orchestrating workflow execution.

    The orchestrator manages the execution of workflows by:
    1. Breaking down workflows into tasks
    2. Assigning tasks to appropriate agents
    3. Monitoring task execution progress
    4. Handling failures and retries
    5. Coordinating communication between agents

    Attributes:
        registered_agents (Dict[str, BaseAgent]): Mapping of agent IDs to instances
        active_workflows (Dict[str, Workflow]): Currently executing workflows
        task_assignments (Dict[str, str]): Mapping of task IDs to agent IDs
        message_bus (MessageBus): Central message bus for agent communication
    """

    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        """Initialize the orchestrator agent.

        Args:
            config: Configuration parameters
            message_bus: Message bus for agent communication
        """
        super().__init__(config, message_bus)

        self.registered_agents: Dict[str, BaseAgent] = {}
        self.active_workflows: Dict[str, Workflow] = {}
        self.task_assignments: Dict[str, str] = {}
        self.agent_capabilities: Dict[str, Dict[str, Any]] = {}

        # Additional message handlers for orchestrator-specific messages
        if self.protocol:
            self.protocol.register_handler(
                MessageType.STATUS_UPDATE, self._handle_status_update
            )

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: The agent instance to register
        """
        self.registered_agents[agent.agent_id] = agent

        # Request agent capabilities
        if self.protocol:
            asyncio.create_task(self._request_agent_capabilities(agent.agent_id))

    async def _request_agent_capabilities(self, agent_id: str):
        """Request capabilities from a registered agent.

        Args:
            agent_id: ID of the agent to request capabilities from
        """
        if not self.protocol:
            return

        try:
            message_id = await self.protocol.send_message(
                recipient=agent_id,
                message_type=MessageType.CAPABILITY_REQUEST,
                content={},
                priority=MessagePriority.NORMAL,
            )

            # Store message ID for correlation
            self.pending_capability_requests[agent_id] = message_id

        except Exception as e:
            logger.error(
                f"Error requesting capabilities from agent {agent_id}: {str(e)}"
            )

    async def _handle_status_update(self, message: Message):
        """Handle status updates from agents.

        Args:
            message: The status update message
        """
        try:
            task_id = message.content.get("task_id")
            status = message.content["status"]
            details = message.content.get("details", {})

            if task_id and task_id in self.task_assignments:
                await self._update_task_status(task_id, status, details)

        except Exception as e:
            logger.error(f"Error handling status update: {str(e)}")

    async def _update_task_status(
        self, task_id: str, status: str, details: Dict[str, Any]
    ):
        """Update the status of a task and handle workflow progression.

        Args:
            task_id: ID of the task to update
            status: New status
            details: Additional status details
        """
        # Find workflow containing this task
        workflow_id = None
        for wf_id, workflow in self.active_workflows.items():
            if task_id in workflow.tasks:
                workflow_id = wf_id
                break

        if not workflow_id:
            logger.warning(f"Received status update for unknown task: {task_id}")
            return

        workflow = self.active_workflows[workflow_id]

        # Update task status
        workflow.tasks[task_id].status = status
        workflow.tasks[task_id].details.update(details)

        # Check if workflow is complete
        if self._check_workflow_complete(workflow):
            await self._handle_workflow_completion(workflow_id)
        elif status == TaskStatus.FAILED:
            await self._handle_task_failure(workflow_id, task_id)
        else:
            # Schedule next tasks if current task is complete
            if status == TaskStatus.COMPLETED:
                await self._schedule_next_tasks(workflow_id, task_id)

    def _check_workflow_complete(self, workflow: Workflow) -> bool:
        """Check if all tasks in a workflow are complete.

        Args:
            workflow: The workflow to check

        Returns:
            True if all tasks are complete, False otherwise
        """
        return all(
            task.status == TaskStatus.COMPLETED for task in workflow.tasks.values()
        )

    async def _handle_workflow_completion(self, workflow_id: str):
        """Handle completion of a workflow.

        Args:
            workflow_id: ID of the completed workflow
        """
        workflow = self.active_workflows[workflow_id]

        # Notify relevant agents of completion
        if self.protocol:
            for agent_id in set(self.task_assignments.values()):
                await self.protocol.send_status_update(
                    recipient=agent_id,
                    status="workflow_complete",
                    details={"workflow_id": workflow_id, "metrics": workflow.metrics},
                )

        # Clean up workflow data
        del self.active_workflows[workflow_id]

        # Remove task assignments for this workflow
        self.task_assignments = {
            task_id: agent_id
            for task_id, agent_id in self.task_assignments.items()
            if task_id not in workflow.tasks
        }

    async def _handle_task_failure(self, workflow_id: str, task_id: str):
        """Handle failure of a task within a workflow.

        Args:
            workflow_id: ID of the workflow containing the failed task
            task_id: ID of the failed task
        """
        workflow = self.active_workflows[workflow_id]
        task = workflow.tasks[task_id]

        if task.retries < workflow.max_retries:
            # Retry the task
            task.retries += 1
            task.status = TaskStatus.PENDING
            await self._assign_task(workflow_id, task_id)
        else:
            # Mark workflow as failed
            workflow.status = "failed"

            # Notify agents
            if self.protocol:
                for agent_id in set(self.task_assignments.values()):
                    await self.protocol.send_status_update(
                        recipient=agent_id,
                        status="workflow_failed",
                        details={
                            "workflow_id": workflow_id,
                            "failed_task": task_id,
                            "error": task.details.get("error"),
                        },
                    )

    async def _schedule_next_tasks(self, workflow_id: str, completed_task_id: str):
        """Schedule tasks that depend on a completed task.

        Args:
            workflow_id: ID of the workflow
            completed_task_id: ID of the completed task
        """
        workflow = self.active_workflows[workflow_id]

        # Find tasks that depend on the completed task
        for task_id, task in workflow.tasks.items():
            if (
                task.status == TaskStatus.PENDING
                and completed_task_id in task.dependencies
            ):
                # Check if all dependencies are complete
                if all(
                    workflow.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                ):
                    await self._assign_task(workflow_id, task_id)

    async def _assign_task(self, workflow_id: str, task_id: str):
        """Assign a task to an appropriate agent.

        Args:
            workflow_id: ID of the workflow
            task_id: ID of the task to assign
        """
        workflow = self.active_workflows[workflow_id]
        task = workflow.tasks[task_id]

        # Find suitable agent based on capabilities
        agent_id = self._find_suitable_agent(task)
        if not agent_id:
            logger.error(f"No suitable agent found for task {task_id}")
            task.status = TaskStatus.FAILED
            task.details["error"] = "No suitable agent available"
            return

        # Assign task
        self.task_assignments[task_id] = agent_id

        # Request task execution
        if self.protocol:
            try:
                await self.protocol.request_task(
                    recipient=agent_id,
                    task_description=task.description,
                    parameters=task.parameters,
                    priority=MessagePriority.NORMAL,
                    metadata={"workflow_id": workflow_id, "task_id": task_id},
                )

                task.status = TaskStatus.RUNNING

            except Exception as e:
                logger.error(
                    f"Error assigning task {task_id} to agent {agent_id}: {str(e)}"
                )
                task.status = TaskStatus.FAILED
                task.details["error"] = str(e)

    def _find_suitable_agent(self, task: Task) -> Optional[str]:
        """Find an agent capable of handling a task.

        Args:
            task: The task to find an agent for

        Returns:
            ID of suitable agent, or None if none found
        """
        for agent_id, capabilities in self.agent_capabilities.items():
            if task.type in capabilities["supported_tasks"]:
                return agent_id
        return None

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute an orchestrator task.

        The orchestrator primarily handles workflow management tasks.

        Args:
            task: The task to execute

        Returns:
            Task execution results

        Raises:
            TaskExecutionError: If task execution fails
        """
        try:
            if task.type == "start_workflow":
                workflow_id = await self._start_workflow(task.parameters["workflow"])
                return {"status": "completed", "output": {"workflow_id": workflow_id}}

            elif task.type == "stop_workflow":
                await self._stop_workflow(task.parameters["workflow_id"])
                return {"status": "completed"}

            else:
                raise TaskExecutionError(f"Unknown task type: {task.type}")

        except Exception as e:
            raise TaskExecutionError(str(e))

    async def _start_workflow(self, workflow: Workflow) -> str:
        """Start execution of a new workflow.

        Args:
            workflow: The workflow to execute

        Returns:
            The workflow ID

        Raises:
            WorkflowError: If workflow initialization fails
        """
        workflow_id = str(uuid4())
        self.active_workflows[workflow_id] = workflow

        # Initialize workflow status
        workflow.status = "running"
        workflow.metrics = {"start_time": asyncio.get_event_loop().time()}

        # Schedule initial tasks (those with no dependencies)
        initial_tasks = [
            task_id for task_id, task in workflow.tasks.items() if not task.dependencies
        ]

        for task_id in initial_tasks:
            await self._assign_task(workflow_id, task_id)

        return workflow_id

    async def _stop_workflow(self, workflow_id: str):
        """Stop execution of a workflow.

        Args:
            workflow_id: ID of the workflow to stop

        Raises:
            WorkflowError: If workflow not found or stop fails
        """
        if workflow_id not in self.active_workflows:
            raise WorkflowError(f"Workflow not found: {workflow_id}")

        workflow = self.active_workflows[workflow_id]

        # Notify agents to stop tasks
        if self.protocol:
            for task_id, agent_id in self.task_assignments.items():
                if task_id in workflow.tasks:
                    await self.protocol.send_message(
                        recipient=agent_id,
                        message_type=MessageType.TASK_CANCEL,
                        content={"task_id": task_id},
                        priority=MessagePriority.HIGH,
                    )

        # Update workflow status
        workflow.status = "stopped"
        workflow.metrics["stop_time"] = asyncio.get_event_loop().time()
        workflow.metrics["duration"] = (
            workflow.metrics["stop_time"] - workflow.metrics["start_time"]
        )

        # Clean up
        await self._handle_workflow_completion(workflow_id)

    def _get_supported_tasks(self) -> Dict[str, Any]:
        """Get tasks supported by the orchestrator.

        Returns:
            Dictionary of supported task types and their capabilities
        """
        return {
            "start_workflow": {
                "description": "Start execution of a workflow",
                "parameters": ["workflow"],
                "examples": [{"workflow": {"tasks": {}, "max_retries": 3}}],
            },
            "stop_workflow": {
                "description": "Stop execution of a workflow",
                "parameters": ["workflow_id"],
            },
        }
