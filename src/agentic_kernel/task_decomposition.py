"""Task decomposition system for breaking complex tasks into subtasks.

This module implements a system for decomposing complex tasks into smaller,
more manageable subtasks. It provides mechanisms for defining task decomposition
strategies, managing dependencies between subtasks, and tracking their execution.

Key features:
1. Task decomposition strategies
2. Subtask dependency management
3. Subtask allocation to specialized agents
4. Execution tracking and coordination
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import Field
from .types import Task, TaskStatus, WorkflowStep
from .task_manager import TaskManager
from .communication.protocol import CommunicationProtocol
from .communication.message import MessageType

logger = logging.getLogger(__name__)


class SubTask(Task):
    """A subtask created by decomposing a complex task.

    This class extends the base Task class with additional properties
    specific to subtasks, such as the parent task ID and dependency information.

    Attributes:
        parent_task_id: ID of the parent task this subtask belongs to
        dependencies: IDs of other subtasks this subtask depends on
        complexity: Estimated complexity score (0.0-1.0)
        is_critical: Whether this subtask is critical for the parent task
    """

    parent_task_id: str
    dependencies: List[str] = Field(default_factory=list)
    complexity: float = 0.5
    is_critical: bool = False

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        agent_type: str,
        parameters: Dict[str, Any],
        parent_task_id: str,
        dependencies: Optional[List[str]] = None,
        complexity: float = 0.5,
        is_critical: bool = False,
        **kwargs
    ) -> "SubTask":
        """Create a new subtask.

        This factory method creates a new subtask with the given properties.

        Args:
            name: Name of the subtask
            description: Description of what the subtask does
            agent_type: Type of agent qualified to execute this subtask
            parameters: Configuration parameters for subtask execution
            parent_task_id: ID of the parent task this subtask belongs to
            dependencies: IDs of other subtasks this subtask depends on
            complexity: Estimated complexity score (0.0-1.0)
            is_critical: Whether this subtask is critical for the parent task
            **kwargs: Additional arguments to pass to the parent Task constructor

        Returns:
            A new SubTask instance
        """
        # Create a dictionary with all the fields
        data = {
            "name": name,
            "description": description,
            "agent_type": agent_type,
            "parameters": parameters,
            "parent_task_id": parent_task_id,
            "complexity": complexity,
            "is_critical": is_critical,
            **kwargs
        }

        if dependencies:
            data["dependencies"] = dependencies

        # Create the instance
        return cls(**data)

    def __init__(
        self,
        name: str,
        description: str,
        agent_type: str,
        parameters: Dict[str, Any],
        parent_task_id: str,
        dependencies: Optional[List[str]] = None,
        complexity: float = 0.5,
        is_critical: bool = False,
        **kwargs
    ):
        """Initialize a subtask.

        Args:
            name: Name of the subtask
            description: Description of what the subtask does
            agent_type: Type of agent qualified to execute this subtask
            parameters: Configuration parameters for subtask execution
            parent_task_id: ID of the parent task this subtask belongs to
            dependencies: IDs of other subtasks this subtask depends on
            complexity: Estimated complexity score (0.0-1.0)
            is_critical: Whether this subtask is critical for the parent task
            **kwargs: Additional arguments to pass to the parent Task constructor
        """
        # Pass all arguments to the parent class constructor
        super().__init__(
            name=name,
            description=description,
            agent_type=agent_type,
            parameters=parameters,
            parent_task_id=parent_task_id,
            dependencies=dependencies or [],
            complexity=complexity,
            is_critical=is_critical,
            **kwargs
        )


class ComplexTask(Task):
    """A complex task that can be decomposed into subtasks.

    This class extends the base Task class with properties and methods
    specific to complex tasks that can be decomposed into subtasks.

    Attributes:
        subtasks: List of subtasks this complex task has been decomposed into
        decomposition_strategy: Strategy used for decomposing this task
        is_decomposed: Whether this task has been decomposed
    """

    subtasks: List[SubTask] = Field(default_factory=list)
    decomposition_strategy: Optional[str] = None
    is_decomposed: bool = False

    def __init__(
        self,
        name: str,
        description: str,
        agent_type: str,
        parameters: Dict[str, Any],
        decomposition_strategy: Optional[str] = None,
        **kwargs
    ):
        """Initialize a complex task.

        Args:
            name: Name of the complex task
            description: Description of what the task does
            agent_type: Type of agent qualified to execute this task
            parameters: Configuration parameters for task execution
            decomposition_strategy: Strategy to use for decomposing this task
            **kwargs: Additional arguments to pass to the parent Task constructor
        """
        super().__init__(
            name=name,
            description=description,
            agent_type=agent_type,
            parameters=parameters,
            **kwargs
        )
        if decomposition_strategy:
            self.decomposition_strategy = decomposition_strategy

    def add_subtask(self, subtask: SubTask) -> None:
        """Add a subtask to this complex task.

        Args:
            subtask: The subtask to add
        """
        self.subtasks.append(subtask)

    def get_subtask(self, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask by its ID.

        Args:
            subtask_id: ID of the subtask to get

        Returns:
            The subtask if found, None otherwise
        """
        for subtask in self.subtasks:
            if subtask.id == subtask_id:
                return subtask
        return None

    def get_ready_subtasks(self) -> List[SubTask]:
        """Get subtasks that are ready to be executed.

        A subtask is ready if all its dependencies have been completed.

        Returns:
            List of subtasks ready for execution
        """
        completed_subtask_ids = {
            subtask.id for subtask in self.subtasks 
            if subtask.status == "completed"
        }

        ready_subtasks = []
        for subtask in self.subtasks:
            if subtask.status == "pending":
                # Check if all dependencies are completed
                if all(dep_id in completed_subtask_ids for dep_id in subtask.dependencies):
                    ready_subtasks.append(subtask)

        return ready_subtasks

    def is_complete(self) -> bool:
        """Check if all subtasks have been completed.

        Returns:
            True if all subtasks are completed, False otherwise
        """
        if not self.subtasks:
            return False

        return all(subtask.status == "completed" for subtask in self.subtasks)

    def get_progress(self) -> float:
        """Get the progress of this complex task.

        Returns:
            Progress as a float between 0.0 and 1.0
        """
        if not self.subtasks:
            return 0.0

        completed = sum(1 for subtask in self.subtasks if subtask.status == "completed")
        return completed / len(self.subtasks)


class DecompositionStrategy:
    """Base class for task decomposition strategies.

    This abstract class defines the interface for task decomposition strategies.
    Concrete strategies should implement the decompose method.
    """

    def __init__(self, name: str, description: str):
        """Initialize a decomposition strategy.

        Args:
            name: Name of the strategy
            description: Description of what the strategy does
        """
        self.name = name
        self.description = description

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a complex task into subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement decompose()")


class TaskDecomposer:
    """System for decomposing complex tasks into subtasks.

    This class provides the core functionality for decomposing complex tasks
    into subtasks, managing dependencies between subtasks, and coordinating
    their execution.

    Attributes:
        task_manager: Reference to the task manager
        protocol: Optional communication protocol for agent communication
        strategies: Dictionary of available decomposition strategies
    """

    def __init__(
        self,
        task_manager: TaskManager,
        protocol: Optional[CommunicationProtocol] = None
    ):
        """Initialize the task decomposer.

        Args:
            task_manager: Reference to the task manager
            protocol: Optional communication protocol for agent communication
        """
        self.task_manager = task_manager
        self.protocol = protocol
        self.strategies: Dict[str, DecompositionStrategy] = {}
        self.complex_tasks: Dict[str, ComplexTask] = {}

    def register_strategy(self, strategy: DecompositionStrategy) -> None:
        """Register a decomposition strategy.

        Args:
            strategy: The strategy to register
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"Registered decomposition strategy: {strategy.name}")

    def create_complex_task(
        self,
        name: str,
        description: str,
        agent_type: str,
        parameters: Dict[str, Any],
        decomposition_strategy: Optional[str] = None,
    ) -> ComplexTask:
        """Create a new complex task.

        Args:
            name: Name of the complex task
            description: Description of what the task does
            agent_type: Type of agent qualified to execute this task
            parameters: Configuration parameters for task execution
            decomposition_strategy: Strategy to use for decomposing this task

        Returns:
            The newly created complex task
        """
        task = ComplexTask(
            name=name,
            description=description,
            agent_type=agent_type,
            parameters=parameters,
            decomposition_strategy=decomposition_strategy,
        )

        # Register with task manager
        self.task_manager.task_ledger.add_task(task)
        self.task_manager.active_tasks[task.id] = task

        # Store in our complex tasks dictionary
        self.complex_tasks[task.id] = task

        logger.info(f"Created complex task {task.id}: {description}")
        return task

    async def decompose_task(
        self,
        task_id: str,
        strategy_name: Optional[str] = None,
    ) -> List[SubTask]:
        """Decompose a complex task into subtasks.

        Args:
            task_id: ID of the complex task to decompose
            strategy_name: Name of the strategy to use (overrides task's strategy)

        Returns:
            List of created subtasks

        Raises:
            ValueError: If the task is not found or the strategy is invalid
        """
        # Get the complex task
        if task_id not in self.complex_tasks:
            raise ValueError(f"Complex task not found: {task_id}")

        task = self.complex_tasks[task_id]

        # Determine the strategy to use
        strategy_name = strategy_name or task.decomposition_strategy
        if not strategy_name or strategy_name not in self.strategies:
            raise ValueError(f"Invalid decomposition strategy: {strategy_name}")

        strategy = self.strategies[strategy_name]

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Register subtasks with task manager and add to complex task
        for subtask in subtasks:
            self.task_manager.task_ledger.add_task(subtask)
            self.task_manager.active_tasks[subtask.id] = subtask
            task.add_subtask(subtask)

        # Mark the task as decomposed
        task.is_decomposed = True

        # If we have a protocol, send task decomposition message
        if self.protocol:
            # Prepare subtask descriptions
            subtask_descriptions = []
            dependencies = {}
            complexity_estimates = {}

            for subtask in subtasks:
                subtask_descriptions.append({
                    "id": subtask.id,
                    "name": subtask.name,
                    "description": subtask.description,
                    "agent_type": subtask.agent_type,
                    "parameters": subtask.parameters,
                })

                if subtask.dependencies:
                    dependencies[subtask.id] = subtask.dependencies

                complexity_estimates[subtask.id] = subtask.complexity

            # Send decomposition message
            await self.protocol.send_task_decomposition(
                recipient=task.agent_type,  # Send to the agent type that handles this task
                parent_task_id=task.id,
                subtasks=subtask_descriptions,
                dependencies=dependencies,
                estimated_complexity=complexity_estimates,
            )

        logger.info(f"Decomposed task {task_id} into {len(subtasks)} subtasks")
        return subtasks

    async def execute_subtasks(self, task_id: str) -> bool:
        """Execute all ready subtasks for a complex task.

        This method finds all subtasks that are ready to be executed
        (i.e., all their dependencies have been completed) and starts
        their execution.

        Args:
            task_id: ID of the complex task

        Returns:
            True if all subtasks are now complete, False otherwise

        Raises:
            ValueError: If the task is not found
        """
        # Get the complex task
        if task_id not in self.complex_tasks:
            raise ValueError(f"Complex task not found: {task_id}")

        task = self.complex_tasks[task_id]

        # Get ready subtasks
        ready_subtasks = task.get_ready_subtasks()

        # Start execution of ready subtasks
        for subtask in ready_subtasks:
            # Update status to running
            self.task_manager.update_task_status(subtask.id, "running")

            # In a real implementation, we would delegate the subtask to an agent
            # For now, we'll just log that we're executing it
            logger.info(f"Executing subtask {subtask.id}: {subtask.name}")

        # Check if all subtasks are complete
        return task.is_complete()

    def get_task_progress(self, task_id: str) -> float:
        """Get the progress of a complex task.

        Args:
            task_id: ID of the complex task

        Returns:
            Progress as a float between 0.0 and 1.0

        Raises:
            ValueError: If the task is not found
        """
        # Get the complex task
        if task_id not in self.complex_tasks:
            raise ValueError(f"Complex task not found: {task_id}")

        task = self.complex_tasks[task_id]
        return task.get_progress()

    def create_workflow_from_task(self, task_id: str) -> List[WorkflowStep]:
        """Create a workflow from a decomposed task.

        This method converts a decomposed task into a workflow that can be
        executed by the workflow engine.

        Args:
            task_id: ID of the complex task

        Returns:
            List of workflow steps

        Raises:
            ValueError: If the task is not found or not decomposed
        """
        # Get the complex task
        if task_id not in self.complex_tasks:
            raise ValueError(f"Complex task not found: {task_id}")

        task = self.complex_tasks[task_id]

        if not task.is_decomposed:
            raise ValueError(f"Task {task_id} has not been decomposed")

        # Create workflow steps
        workflow_steps = []

        for subtask in task.subtasks:
            step = WorkflowStep(
                task=subtask,
                dependencies=subtask.dependencies,
                parallel=True,  # Allow parallel execution where possible
            )
            workflow_steps.append(step)

        return workflow_steps
