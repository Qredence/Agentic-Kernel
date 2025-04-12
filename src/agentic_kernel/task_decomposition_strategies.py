"""Concrete implementations of task decomposition strategies.

This module provides concrete implementations of task decomposition strategies
that can be used with the TaskDecomposer to break complex tasks into subtasks.

Each strategy implements a different approach to task decomposition, such as:
1. Sequential decomposition (breaking a task into sequential steps)
2. Parallel decomposition (breaking a task into parallel subtasks)
3. Hierarchical decomposition (breaking a task into a hierarchy of subtasks)
4. Domain-specific decomposition (using domain knowledge to decompose tasks)
"""

import logging
from typing import Any, Dict, List, Optional

from .task_decomposition import ComplexTask, DecompositionStrategy, SubTask

logger = logging.getLogger(__name__)


class SequentialDecompositionStrategy(DecompositionStrategy):
    """Strategy for decomposing a task into sequential steps.

    This strategy breaks a complex task into a sequence of subtasks that must
    be executed in order, with each subtask depending on the previous one.
    """

    def __init__(self):
        """Initialize the sequential decomposition strategy."""
        super().__init__(
            name="sequential",
            description="Decomposes a task into sequential steps",
        )

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a complex task into sequential subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks in sequential order
        """
        # Get the steps from the task parameters
        steps = task.parameters.get("steps", [])
        if not steps:
            logger.warning(f"No steps provided for sequential decomposition of task {task.id}")
            return []

        subtasks = []
        previous_subtask_id = None

        for i, step in enumerate(steps):
            # Create a subtask for this step
            subtask = SubTask(
                name=f"{task.name}_step_{i+1}",
                description=step.get("description", f"Step {i+1} of {task.name}"),
                agent_type=step.get("agent_type", task.agent_type),
                parameters=step.get("parameters", {}),
                parent_task_id=task.id,
                dependencies=[previous_subtask_id] if previous_subtask_id else [],
                complexity=step.get("complexity", 0.5),
                is_critical=step.get("is_critical", True),
            )

            subtasks.append(subtask)
            previous_subtask_id = subtask.id

        return subtasks


class ParallelDecompositionStrategy(DecompositionStrategy):
    """Strategy for decomposing a task into parallel subtasks.

    This strategy breaks a complex task into multiple subtasks that can be
    executed in parallel, with no dependencies between them.
    """

    def __init__(self):
        """Initialize the parallel decomposition strategy."""
        super().__init__(
            name="parallel",
            description="Decomposes a task into parallel subtasks",
        )

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a complex task into parallel subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks that can be executed in parallel
        """
        # Get the subtasks from the task parameters
        subtask_specs = task.parameters.get("subtasks", [])
        if not subtask_specs:
            logger.warning(f"No subtasks provided for parallel decomposition of task {task.id}")
            return []

        subtasks = []

        for i, spec in enumerate(subtask_specs):
            # Create a subtask for this specification
            subtask = SubTask(
                name=spec.get("name", f"{task.name}_subtask_{i+1}"),
                description=spec.get("description", f"Subtask {i+1} of {task.name}"),
                agent_type=spec.get("agent_type", task.agent_type),
                parameters=spec.get("parameters", {}),
                parent_task_id=task.id,
                dependencies=[],  # No dependencies for parallel execution
                complexity=spec.get("complexity", 0.5),
                is_critical=spec.get("is_critical", False),
            )

            subtasks.append(subtask)

        return subtasks


class HierarchicalDecompositionStrategy(DecompositionStrategy):
    """Strategy for decomposing a task into a hierarchy of subtasks.

    This strategy breaks a complex task into a hierarchy of subtasks, with
    higher-level subtasks depending on the completion of their child subtasks.
    """

    def __init__(self):
        """Initialize the hierarchical decomposition strategy."""
        super().__init__(
            name="hierarchical",
            description="Decomposes a task into a hierarchy of subtasks",
        )

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a complex task into a hierarchy of subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks in a hierarchical structure
        """
        # Get the hierarchy from the task parameters
        hierarchy = task.parameters.get("hierarchy", {})
        if not hierarchy:
            logger.warning(f"No hierarchy provided for hierarchical decomposition of task {task.id}")
            return []

        # Process the hierarchy recursively
        subtasks = []
        self._process_hierarchy_node(
            task=task,
            node=hierarchy,
            parent_id=None,
            subtasks=subtasks,
            path=[],
        )

        return subtasks

    def _process_hierarchy_node(
        self,
        task: ComplexTask,
        node: Dict[str, Any],
        parent_id: Optional[str],
        subtasks: List[SubTask],
        path: List[str],
    ) -> str:
        """Process a node in the hierarchy and create subtasks.

        Args:
            task: The complex task being decomposed
            node: The hierarchy node to process
            parent_id: ID of the parent subtask, if any
            subtasks: List to add created subtasks to
            path: Path to this node in the hierarchy

        Returns:
            ID of the subtask created for this node
        """
        # Create a subtask for this node
        subtask = SubTask(
            name=node.get("name", f"{task.name}_{'_'.join(path)}"),
            description=node.get("description", f"Subtask at {'.'.join(path) or 'root'} of {task.name}"),
            agent_type=node.get("agent_type", task.agent_type),
            parameters=node.get("parameters", {}),
            parent_task_id=task.id,
            dependencies=[parent_id] if parent_id else [],
            complexity=node.get("complexity", 0.5),
            is_critical=node.get("is_critical", True),
        )

        subtasks.append(subtask)

        # Process children
        children = node.get("children", [])
        child_ids = []

        for i, child in enumerate(children):
            child_path = path + [str(i)]
            child_id = self._process_hierarchy_node(
                task=task,
                node=child,
                parent_id=subtask.id,
                subtasks=subtasks,
                path=child_path,
            )
            child_ids.append(child_id)

        # If this node depends on its children, add dependencies
        if node.get("depends_on_children", False) and child_ids:
            subtask.dependencies.extend(child_ids)

        return subtask.id


class DomainSpecificDecompositionStrategy(DecompositionStrategy):
    """Base class for domain-specific decomposition strategies.

    This class serves as a base for domain-specific decomposition strategies
    that use domain knowledge to decompose tasks in a particular domain.
    Subclasses should implement the decompose method with domain-specific logic.
    """

    def __init__(self, name: str, description: str, domain: str):
        """Initialize a domain-specific decomposition strategy.

        Args:
            name: Name of the strategy
            description: Description of what the strategy does
            domain: The domain this strategy is specialized for
        """
        super().__init__(name=name, description=description)
        self.domain = domain


class SoftwareDevelopmentDecompositionStrategy(DomainSpecificDecompositionStrategy):
    """Strategy for decomposing software development tasks.

    This strategy breaks a software development task into common phases such as
    requirements gathering, design, implementation, testing, and deployment.
    """

    def __init__(self):
        """Initialize the software development decomposition strategy."""
        super().__init__(
            name="software_development",
            description="Decomposes a task into software development phases",
            domain="software_development",
        )

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a software development task into phase-based subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks representing software development phases
        """
        # Define the standard software development phases
        phases = [
            {
                "name": "requirements",
                "description": "Gather and analyze requirements",
                "agent_type": "requirements_analyst",
                "parameters": task.parameters.get("requirements_parameters", {}),
                "complexity": 0.7,
                "is_critical": True,
            },
            {
                "name": "design",
                "description": "Create software design and architecture",
                "agent_type": "software_architect",
                "parameters": task.parameters.get("design_parameters", {}),
                "complexity": 0.8,
                "is_critical": True,
            },
            {
                "name": "implementation",
                "description": "Implement the software according to design",
                "agent_type": "developer",
                "parameters": task.parameters.get("implementation_parameters", {}),
                "complexity": 0.9,
                "is_critical": True,
            },
            {
                "name": "testing",
                "description": "Test the software implementation",
                "agent_type": "tester",
                "parameters": task.parameters.get("testing_parameters", {}),
                "complexity": 0.7,
                "is_critical": True,
            },
            {
                "name": "deployment",
                "description": "Deploy the software to production",
                "agent_type": "devops_engineer",
                "parameters": task.parameters.get("deployment_parameters", {}),
                "complexity": 0.6,
                "is_critical": True,
            },
        ]

        # Override with custom phases if provided
        custom_phases = task.parameters.get("phases", [])
        if custom_phases:
            phases = custom_phases

        subtasks = []
        previous_subtask_id = None

        for i, phase in enumerate(phases):
            # Create a subtask for this phase
            subtask = SubTask(
                name=f"{task.name}_{phase['name']}",
                description=phase.get("description", f"Phase {i+1} of {task.name}"),
                agent_type=phase.get("agent_type", task.agent_type),
                parameters=phase.get("parameters", {}),
                parent_task_id=task.id,
                dependencies=[previous_subtask_id] if previous_subtask_id else [],
                complexity=phase.get("complexity", 0.5),
                is_critical=phase.get("is_critical", True),
            )

            subtasks.append(subtask)
            previous_subtask_id = subtask.id

        return subtasks


class DataAnalysisDecompositionStrategy(DomainSpecificDecompositionStrategy):
    """Strategy for decomposing data analysis tasks.

    This strategy breaks a data analysis task into common phases such as
    data collection, data cleaning, exploratory analysis, modeling, and reporting.
    """

    def __init__(self):
        """Initialize the data analysis decomposition strategy."""
        super().__init__(
            name="data_analysis",
            description="Decomposes a task into data analysis phases",
            domain="data_analysis",
        )

    def decompose(self, task: ComplexTask) -> List[SubTask]:
        """Decompose a data analysis task into phase-based subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks representing data analysis phases
        """
        # Define the standard data analysis phases
        phases = [
            {
                "name": "data_collection",
                "description": "Collect and gather data from various sources",
                "agent_type": "data_collector",
                "parameters": task.parameters.get("collection_parameters", {}),
                "complexity": 0.6,
                "is_critical": True,
            },
            {
                "name": "data_cleaning",
                "description": "Clean and preprocess the collected data",
                "agent_type": "data_engineer",
                "parameters": task.parameters.get("cleaning_parameters", {}),
                "complexity": 0.7,
                "is_critical": True,
            },
            {
                "name": "exploratory_analysis",
                "description": "Perform exploratory data analysis",
                "agent_type": "data_analyst",
                "parameters": task.parameters.get("exploration_parameters", {}),
                "complexity": 0.8,
                "is_critical": True,
            },
            {
                "name": "modeling",
                "description": "Build and train analytical models",
                "agent_type": "data_scientist",
                "parameters": task.parameters.get("modeling_parameters", {}),
                "complexity": 0.9,
                "is_critical": True,
            },
            {
                "name": "reporting",
                "description": "Create reports and visualizations of findings",
                "agent_type": "data_visualizer",
                "parameters": task.parameters.get("reporting_parameters", {}),
                "complexity": 0.7,
                "is_critical": True,
            },
        ]

        # Override with custom phases if provided
        custom_phases = task.parameters.get("phases", [])
        if custom_phases:
            phases = custom_phases

        subtasks = []
        previous_subtask_id = None

        for i, phase in enumerate(phases):
            # Create a subtask for this phase
            subtask = SubTask(
                name=f"{task.name}_{phase['name']}",
                description=phase.get("description", f"Phase {i+1} of {task.name}"),
                agent_type=phase.get("agent_type", task.agent_type),
                parameters=phase.get("parameters", {}),
                parent_task_id=task.id,
                dependencies=[previous_subtask_id] if previous_subtask_id else [],
                complexity=phase.get("complexity", 0.5),
                is_critical=phase.get("is_critical", True),
            )

            subtasks.append(subtask)
            previous_subtask_id = subtask.id

        return subtasks
