"""Tests for the task decomposition system.

This module contains tests for the task decomposition system, including
creating complex tasks, decomposing them using different strategies,
and executing subtasks.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agentic_kernel.task_decomposition import (
    ComplexTask,
    DecompositionStrategy,
    SubTask,
    TaskDecomposer,
)
from src.agentic_kernel.task_decomposition_strategies import (
    SequentialDecompositionStrategy,
    ParallelDecompositionStrategy,
    HierarchicalDecompositionStrategy,
    SoftwareDevelopmentDecompositionStrategy,
    DataAnalysisDecompositionStrategy,
)
from src.agentic_kernel.task_manager import TaskManager
from src.agentic_kernel.ledgers import TaskLedger, ProgressLedger
from src.agentic_kernel.types import Task


class TestSubTask(unittest.TestCase):
    """Tests for the SubTask class."""

    def test_init(self):
        """Test initialization of a subtask."""
        subtask = SubTask(
            name="test_subtask",
            description="A test subtask",
            agent_type="test_agent",
            parameters={"param1": "value1"},
            parent_task_id="parent_task_id",
            dependencies=["dep1", "dep2"],
            complexity=0.7,
            is_critical=True,
        )

        self.assertEqual(subtask.name, "test_subtask")
        self.assertEqual(subtask.description, "A test subtask")
        self.assertEqual(subtask.agent_type, "test_agent")
        self.assertEqual(subtask.parameters, {"param1": "value1"})
        self.assertEqual(subtask.parent_task_id, "parent_task_id")
        self.assertEqual(subtask.dependencies, ["dep1", "dep2"])
        self.assertEqual(subtask.complexity, 0.7)
        self.assertTrue(subtask.is_critical)


class TestComplexTask(unittest.TestCase):
    """Tests for the ComplexTask class."""

    def test_init(self):
        """Test initialization of a complex task."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={"param1": "value1"},
            decomposition_strategy="sequential",
        )

        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.agent_type, "test_agent")
        self.assertEqual(task.parameters, {"param1": "value1"})
        self.assertEqual(task.decomposition_strategy, "sequential")
        self.assertEqual(task.subtasks, [])
        self.assertFalse(task.is_decomposed)

    def test_add_subtask(self):
        """Test adding a subtask to a complex task."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        subtask = SubTask(
            name="test_subtask",
            description="A test subtask",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        task.add_subtask(subtask)
        self.assertEqual(len(task.subtasks), 1)
        self.assertEqual(task.subtasks[0], subtask)

    def test_get_subtask(self):
        """Test getting a subtask by ID."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)

        # Test getting an existing subtask
        result = task.get_subtask(subtask1.id)
        self.assertEqual(result, subtask1)

        # Test getting a non-existent subtask
        result = task.get_subtask("non_existent_id")
        self.assertIsNone(result)

    def test_get_ready_subtasks(self):
        """Test getting subtasks that are ready to be executed."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        # Create subtasks with dependencies
        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
            dependencies=[],
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
            dependencies=[subtask1.id],
        )

        subtask3 = SubTask(
            name="subtask3",
            description="Subtask 3",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
            dependencies=[subtask2.id],
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)
        task.add_subtask(subtask3)

        # Initially, only subtask1 should be ready (no dependencies)
        ready_subtasks = task.get_ready_subtasks()
        self.assertEqual(len(ready_subtasks), 1)
        self.assertEqual(ready_subtasks[0], subtask1)

        # Mark subtask1 as completed
        subtask1.status = "completed"

        # Now subtask2 should be ready
        ready_subtasks = task.get_ready_subtasks()
        self.assertEqual(len(ready_subtasks), 1)
        self.assertEqual(ready_subtasks[0], subtask2)

        # Mark subtask2 as completed
        subtask2.status = "completed"

        # Now subtask3 should be ready
        ready_subtasks = task.get_ready_subtasks()
        self.assertEqual(len(ready_subtasks), 1)
        self.assertEqual(ready_subtasks[0], subtask3)

    def test_is_complete(self):
        """Test checking if all subtasks are completed."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        # With no subtasks, is_complete should return False
        self.assertFalse(task.is_complete())

        # Add some subtasks
        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)

        # With no completed subtasks, is_complete should return False
        self.assertFalse(task.is_complete())

        # Mark one subtask as completed
        subtask1.status = "completed"
        self.assertFalse(task.is_complete())

        # Mark all subtasks as completed
        subtask2.status = "completed"
        self.assertTrue(task.is_complete())

    def test_get_progress(self):
        """Test getting the progress of a complex task."""
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        # With no subtasks, progress should be 0.0
        self.assertEqual(task.get_progress(), 0.0)

        # Add some subtasks
        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask3 = SubTask(
            name="subtask3",
            description="Subtask 3",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask4 = SubTask(
            name="subtask4",
            description="Subtask 4",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)
        task.add_subtask(subtask3)
        task.add_subtask(subtask4)

        # With no completed subtasks, progress should be 0.0
        self.assertEqual(task.get_progress(), 0.0)

        # Mark one subtask as completed (25%)
        subtask1.status = "completed"
        self.assertEqual(task.get_progress(), 0.25)

        # Mark two subtasks as completed (50%)
        subtask2.status = "completed"
        self.assertEqual(task.get_progress(), 0.5)

        # Mark three subtasks as completed (75%)
        subtask3.status = "completed"
        self.assertEqual(task.get_progress(), 0.75)

        # Mark all subtasks as completed (100%)
        subtask4.status = "completed"
        self.assertEqual(task.get_progress(), 1.0)


class MockDecompositionStrategy(DecompositionStrategy):
    """Mock decomposition strategy for testing."""

    def __init__(self):
        """Initialize the mock decomposition strategy."""
        super().__init__(
            name="mock",
            description="Mock decomposition strategy for testing",
        )

    def decompose(self, task: ComplexTask) -> list[SubTask]:
        """Decompose a complex task into subtasks.

        Args:
            task: The complex task to decompose

        Returns:
            List of subtasks
        """
        # Create a simple linear sequence of 3 subtasks
        subtask1 = SubTask(
            name=f"{task.name}_subtask_1",
            description="Subtask 1",
            agent_type=task.agent_type,
            parameters={},
            parent_task_id=task.id,
            dependencies=[],
        )

        subtask2 = SubTask(
            name=f"{task.name}_subtask_2",
            description="Subtask 2",
            agent_type=task.agent_type,
            parameters={},
            parent_task_id=task.id,
            dependencies=[subtask1.id],
        )

        subtask3 = SubTask(
            name=f"{task.name}_subtask_3",
            description="Subtask 3",
            agent_type=task.agent_type,
            parameters={},
            parent_task_id=task.id,
            dependencies=[subtask2.id],
        )

        return [subtask1, subtask2, subtask3]


class TestTaskDecomposer(unittest.IsolatedAsyncioTestCase):
    """Tests for the TaskDecomposer class."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        # Create mock task ledger and progress ledger
        self.task_ledger = MagicMock(spec=TaskLedger)
        self.progress_ledger = MagicMock(spec=ProgressLedger)

        # Create mock task manager
        self.task_manager = TaskManager(
            task_ledger=self.task_ledger,
            progress_ledger=self.progress_ledger,
        )

        # Mock the update_task_status method
        self.task_manager.update_task_status = MagicMock()

        # Create mock protocol
        self.protocol = MagicMock()
        self.protocol.send_task_decomposition = AsyncMock()

        # Create task decomposer
        self.decomposer = TaskDecomposer(
            task_manager=self.task_manager,
            protocol=self.protocol,
        )

        # Register a mock decomposition strategy
        self.mock_strategy = MockDecompositionStrategy()
        self.decomposer.register_strategy(self.mock_strategy)

    def test_register_strategy(self):
        """Test registering a decomposition strategy."""
        strategy = DecompositionStrategy(
            name="test_strategy",
            description="Test strategy",
        )
        self.decomposer.register_strategy(strategy)
        self.assertIn("test_strategy", self.decomposer.strategies)
        self.assertEqual(self.decomposer.strategies["test_strategy"], strategy)

    def test_create_complex_task(self):
        """Test creating a complex task."""
        task = self.decomposer.create_complex_task(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={"param1": "value1"},
            decomposition_strategy="mock",
        )

        self.assertIsInstance(task, ComplexTask)
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.agent_type, "test_agent")
        self.assertEqual(task.parameters, {"param1": "value1"})
        self.assertEqual(task.decomposition_strategy, "mock")
        self.assertEqual(task.subtasks, [])
        self.assertFalse(task.is_decomposed)

        # Check that the task was added to the task manager
        self.task_ledger.add_task.assert_called_once_with(task)
        self.assertIn(task.id, self.task_manager.active_tasks)
        self.assertEqual(self.task_manager.active_tasks[task.id], task)

        # Check that the task was added to the decomposer's complex tasks
        self.assertIn(task.id, self.decomposer.complex_tasks)
        self.assertEqual(self.decomposer.complex_tasks[task.id], task)

    async def test_decompose_task(self):
        """Test decomposing a complex task."""
        # Create a complex task
        task = self.decomposer.create_complex_task(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
            decomposition_strategy="mock",
        )

        # Decompose the task
        subtasks = await self.decomposer.decompose_task(task.id)

        # Check that the task was decomposed
        self.assertEqual(len(subtasks), 3)
        self.assertTrue(task.is_decomposed)
        self.assertEqual(len(task.subtasks), 3)

        # Check that the subtasks were added to the task manager
        self.assertEqual(self.task_ledger.add_task.call_count, 4)  # 1 for task + 3 for subtasks
        for subtask in subtasks:
            self.assertIn(subtask.id, self.task_manager.active_tasks)
            self.assertEqual(self.task_manager.active_tasks[subtask.id], subtask)

        # Check that the protocol was used to send a task decomposition message
        self.protocol.send_task_decomposition.assert_called_once()
        call_args = self.protocol.send_task_decomposition.call_args[1]
        self.assertEqual(call_args["recipient"], "test_agent")
        self.assertEqual(call_args["parent_task_id"], task.id)
        self.assertEqual(len(call_args["subtasks"]), 3)

    async def test_execute_subtasks(self):
        """Test executing subtasks."""
        # Create and decompose a complex task
        task = self.decomposer.create_complex_task(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
            decomposition_strategy="mock",
        )
        subtasks = await self.decomposer.decompose_task(task.id)

        # Execute subtasks
        is_complete = await self.decomposer.execute_subtasks(task.id)
        self.assertFalse(is_complete)

        # Check that the first subtask was marked as running
        self.task_manager.update_task_status.assert_called_once_with(subtasks[0].id, "running")

        # Mark the first subtask as completed
        subtasks[0].status = "completed"
        self.task_manager.update_task_status.reset_mock()

        # Execute subtasks again
        is_complete = await self.decomposer.execute_subtasks(task.id)
        self.assertFalse(is_complete)

        # Check that the second subtask was marked as running
        self.task_manager.update_task_status.assert_called_once_with(subtasks[1].id, "running")

        # Mark the second subtask as completed
        subtasks[1].status = "completed"
        self.task_manager.update_task_status.reset_mock()

        # Execute subtasks again
        is_complete = await self.decomposer.execute_subtasks(task.id)
        self.assertFalse(is_complete)

        # Check that the third subtask was marked as running
        self.task_manager.update_task_status.assert_called_once_with(subtasks[2].id, "running")

        # Mark the third subtask as completed
        subtasks[2].status = "completed"
        self.task_manager.update_task_status.reset_mock()

        # Execute subtasks again
        is_complete = await self.decomposer.execute_subtasks(task.id)
        self.assertTrue(is_complete)

    def test_get_task_progress(self):
        """Test getting the progress of a complex task."""
        # Create a complex task
        task = self.decomposer.create_complex_task(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        # With no subtasks, progress should be 0.0
        progress = self.decomposer.get_task_progress(task.id)
        self.assertEqual(progress, 0.0)

        # Add some subtasks
        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)

        # With no completed subtasks, progress should be 0.0
        progress = self.decomposer.get_task_progress(task.id)
        self.assertEqual(progress, 0.0)

        # Mark one subtask as completed (50%)
        subtask1.status = "completed"
        progress = self.decomposer.get_task_progress(task.id)
        self.assertEqual(progress, 0.5)

        # Mark all subtasks as completed (100%)
        subtask2.status = "completed"
        progress = self.decomposer.get_task_progress(task.id)
        self.assertEqual(progress, 1.0)

    def test_create_workflow_from_task(self):
        """Test creating a workflow from a decomposed task."""
        # Create a complex task
        task = self.decomposer.create_complex_task(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={},
        )

        # Add some subtasks
        subtask1 = SubTask(
            name="subtask1",
            description="Subtask 1",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
            dependencies=[],
        )

        subtask2 = SubTask(
            name="subtask2",
            description="Subtask 2",
            agent_type="test_agent",
            parameters={},
            parent_task_id=task.id,
            dependencies=[subtask1.id],
        )

        task.add_subtask(subtask1)
        task.add_subtask(subtask2)
        task.is_decomposed = True

        # Create workflow
        workflow_steps = self.decomposer.create_workflow_from_task(task.id)

        # Check workflow steps
        self.assertEqual(len(workflow_steps), 2)
        self.assertEqual(workflow_steps[0].task, subtask1)
        self.assertEqual(workflow_steps[0].dependencies, [])
        self.assertTrue(workflow_steps[0].parallel)
        self.assertEqual(workflow_steps[1].task, subtask2)
        self.assertEqual(workflow_steps[1].dependencies, [subtask1.id])
        self.assertTrue(workflow_steps[1].parallel)


class TestSequentialDecompositionStrategy(unittest.TestCase):
    """Tests for the SequentialDecompositionStrategy."""

    def test_decompose(self):
        """Test decomposing a task into sequential subtasks."""
        strategy = SequentialDecompositionStrategy()

        # Create a complex task with steps
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={
                "steps": [
                    {
                        "description": "Step 1",
                        "agent_type": "agent1",
                        "parameters": {"param1": "value1"},
                    },
                    {
                        "description": "Step 2",
                        "agent_type": "agent2",
                        "parameters": {"param2": "value2"},
                    },
                    {
                        "description": "Step 3",
                        "agent_type": "agent3",
                        "parameters": {"param3": "value3"},
                    },
                ]
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created
        self.assertEqual(len(subtasks), 3)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "test_task_step_1")
        self.assertEqual(subtasks[0].description, "Step 1")
        self.assertEqual(subtasks[0].agent_type, "agent1")
        self.assertEqual(subtasks[0].parameters, {"param1": "value1"})
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])

        self.assertEqual(subtasks[1].name, "test_task_step_2")
        self.assertEqual(subtasks[1].description, "Step 2")
        self.assertEqual(subtasks[1].agent_type, "agent2")
        self.assertEqual(subtasks[1].parameters, {"param2": "value2"})
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [subtasks[0].id])

        self.assertEqual(subtasks[2].name, "test_task_step_3")
        self.assertEqual(subtasks[2].description, "Step 3")
        self.assertEqual(subtasks[2].agent_type, "agent3")
        self.assertEqual(subtasks[2].parameters, {"param3": "value3"})
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [subtasks[1].id])


class TestParallelDecompositionStrategy(unittest.TestCase):
    """Tests for the ParallelDecompositionStrategy."""

    def test_decompose(self):
        """Test decomposing a task into parallel subtasks."""
        strategy = ParallelDecompositionStrategy()

        # Create a complex task with subtasks
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={
                "subtasks": [
                    {
                        "name": "subtask1",
                        "description": "Subtask 1",
                        "agent_type": "agent1",
                        "parameters": {"param1": "value1"},
                    },
                    {
                        "name": "subtask2",
                        "description": "Subtask 2",
                        "agent_type": "agent2",
                        "parameters": {"param2": "value2"},
                    },
                    {
                        "name": "subtask3",
                        "description": "Subtask 3",
                        "agent_type": "agent3",
                        "parameters": {"param3": "value3"},
                    },
                ]
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created
        self.assertEqual(len(subtasks), 3)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "subtask1")
        self.assertEqual(subtasks[0].description, "Subtask 1")
        self.assertEqual(subtasks[0].agent_type, "agent1")
        self.assertEqual(subtasks[0].parameters, {"param1": "value1"})
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])

        self.assertEqual(subtasks[1].name, "subtask2")
        self.assertEqual(subtasks[1].description, "Subtask 2")
        self.assertEqual(subtasks[1].agent_type, "agent2")
        self.assertEqual(subtasks[1].parameters, {"param2": "value2"})
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [])

        self.assertEqual(subtasks[2].name, "subtask3")
        self.assertEqual(subtasks[2].description, "Subtask 3")
        self.assertEqual(subtasks[2].agent_type, "agent3")
        self.assertEqual(subtasks[2].parameters, {"param3": "value3"})
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [])


class TestHierarchicalDecompositionStrategy(unittest.TestCase):
    """Tests for the HierarchicalDecompositionStrategy."""

    def test_decompose(self):
        """Test decomposing a task into a hierarchy of subtasks."""
        strategy = HierarchicalDecompositionStrategy()

        # Create a complex task with a hierarchy
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={
                "hierarchy": {
                    "name": "root_task",
                    "description": "Root task",
                    "agent_type": "root_agent",
                    "parameters": {"root_param": "root_value"},
                    "is_critical": True,
                    "children": [
                        {
                            "name": "child1",
                            "description": "Child task 1",
                            "agent_type": "child_agent",
                            "parameters": {"child_param": "child1_value"},
                            "is_critical": True,
                            "children": [
                                {
                                    "name": "grandchild1",
                                    "description": "Grandchild task 1",
                                    "agent_type": "grandchild_agent",
                                    "parameters": {"grandchild_param": "grandchild1_value"},
                                }
                            ]
                        },
                        {
                            "name": "child2",
                            "description": "Child task 2",
                            "agent_type": "child_agent",
                            "parameters": {"child_param": "child2_value"},
                            "depends_on_children": True,
                            "children": [
                                {
                                    "name": "grandchild2",
                                    "description": "Grandchild task 2",
                                    "agent_type": "grandchild_agent",
                                    "parameters": {"grandchild_param": "grandchild2_value"},
                                }
                            ]
                        }
                    ]
                }
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created
        self.assertEqual(len(subtasks), 5)

        # Extract subtasks by name for easier testing
        root_task = next(st for st in subtasks if st.name == "root_task")
        child1 = next(st for st in subtasks if st.name == "child1")
        child2 = next(st for st in subtasks if st.name == "child2")
        grandchild1 = next(st for st in subtasks if st.name == "grandchild1")
        grandchild2 = next(st for st in subtasks if st.name == "grandchild2")

        # Check root task properties
        self.assertEqual(root_task.description, "Root task")
        self.assertEqual(root_task.agent_type, "root_agent")
        self.assertEqual(root_task.parameters, {"root_param": "root_value"})
        self.assertEqual(root_task.parent_task_id, task.id)
        self.assertEqual(root_task.dependencies, [])
        self.assertTrue(root_task.is_critical)

        # Check child1 properties
        self.assertEqual(child1.description, "Child task 1")
        self.assertEqual(child1.agent_type, "child_agent")
        self.assertEqual(child1.parameters, {"child_param": "child1_value"})
        self.assertEqual(child1.parent_task_id, task.id)
        self.assertEqual(child1.dependencies, [root_task.id])
        self.assertTrue(child1.is_critical)

        # Check child2 properties
        self.assertEqual(child2.description, "Child task 2")
        self.assertEqual(child2.agent_type, "child_agent")
        self.assertEqual(child2.parameters, {"child_param": "child2_value"})
        self.assertEqual(child2.parent_task_id, task.id)
        # child2 depends on root_task and grandchild2 (depends_on_children=True)
        self.assertIn(root_task.id, child2.dependencies)
        self.assertIn(grandchild2.id, child2.dependencies)

        # Check grandchild1 properties
        self.assertEqual(grandchild1.description, "Grandchild task 1")
        self.assertEqual(grandchild1.agent_type, "grandchild_agent")
        self.assertEqual(grandchild1.parameters, {"grandchild_param": "grandchild1_value"})
        self.assertEqual(grandchild1.parent_task_id, task.id)
        self.assertEqual(grandchild1.dependencies, [child1.id])

        # Check grandchild2 properties
        self.assertEqual(grandchild2.description, "Grandchild task 2")
        self.assertEqual(grandchild2.agent_type, "grandchild_agent")
        self.assertEqual(grandchild2.parameters, {"grandchild_param": "grandchild2_value"})
        self.assertEqual(grandchild2.parent_task_id, task.id)
        self.assertEqual(grandchild2.dependencies, [child2.id])

    def test_decompose_empty_hierarchy(self):
        """Test decomposing a task with an empty hierarchy."""
        strategy = HierarchicalDecompositionStrategy()

        # Create a complex task with an empty hierarchy
        task = ComplexTask(
            name="test_task",
            description="A test task",
            agent_type="test_agent",
            parameters={
                "hierarchy": {}
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that no subtasks were created
        self.assertEqual(len(subtasks), 0)


class TestSoftwareDevelopmentDecompositionStrategy(unittest.TestCase):
    """Tests for the SoftwareDevelopmentDecompositionStrategy."""

    def test_decompose(self):
        """Test decomposing a task into software development phases."""
        strategy = SoftwareDevelopmentDecompositionStrategy()

        # Create a complex task
        task = ComplexTask(
            name="build_app",
            description="Build a new mobile application",
            agent_type="project_manager",
            parameters={},
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created (5 standard phases)
        self.assertEqual(len(subtasks), 5)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "build_app_requirements")
        self.assertEqual(subtasks[0].description, "Gather and analyze requirements")
        self.assertEqual(subtasks[0].agent_type, "requirements_analyst")
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])
        self.assertEqual(subtasks[0].complexity, 0.7)
        self.assertTrue(subtasks[0].is_critical)

        self.assertEqual(subtasks[1].name, "build_app_design")
        self.assertEqual(subtasks[1].description, "Create software design and architecture")
        self.assertEqual(subtasks[1].agent_type, "software_architect")
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [subtasks[0].id])
        self.assertEqual(subtasks[1].complexity, 0.8)
        self.assertTrue(subtasks[1].is_critical)

        self.assertEqual(subtasks[2].name, "build_app_implementation")
        self.assertEqual(subtasks[2].description, "Implement the software according to design")
        self.assertEqual(subtasks[2].agent_type, "developer")
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [subtasks[1].id])
        self.assertEqual(subtasks[2].complexity, 0.9)
        self.assertTrue(subtasks[2].is_critical)

        self.assertEqual(subtasks[3].name, "build_app_testing")
        self.assertEqual(subtasks[3].description, "Test the software implementation")
        self.assertEqual(subtasks[3].agent_type, "tester")
        self.assertEqual(subtasks[3].parent_task_id, task.id)
        self.assertEqual(subtasks[3].dependencies, [subtasks[2].id])
        self.assertEqual(subtasks[3].complexity, 0.7)
        self.assertTrue(subtasks[3].is_critical)

        self.assertEqual(subtasks[4].name, "build_app_deployment")
        self.assertEqual(subtasks[4].description, "Deploy the software to production")
        self.assertEqual(subtasks[4].agent_type, "devops_engineer")
        self.assertEqual(subtasks[4].parent_task_id, task.id)
        self.assertEqual(subtasks[4].dependencies, [subtasks[3].id])
        self.assertEqual(subtasks[4].complexity, 0.6)
        self.assertTrue(subtasks[4].is_critical)

    def test_decompose_with_custom_phases(self):
        """Test decomposing a task with custom software development phases."""
        strategy = SoftwareDevelopmentDecompositionStrategy()

        # Create a complex task with custom phases
        task = ComplexTask(
            name="build_app",
            description="Build a new mobile application",
            agent_type="project_manager",
            parameters={
                "phases": [
                    {
                        "name": "planning",
                        "description": "Plan the project",
                        "agent_type": "project_planner",
                        "parameters": {"timeline": "2 weeks"},
                        "complexity": 0.5,
                        "is_critical": True,
                    },
                    {
                        "name": "coding",
                        "description": "Write the code",
                        "agent_type": "coder",
                        "parameters": {"language": "Swift"},
                        "complexity": 0.8,
                        "is_critical": True,
                    },
                    {
                        "name": "review",
                        "description": "Review the code",
                        "agent_type": "reviewer",
                        "parameters": {"standards": "company_guidelines"},
                        "complexity": 0.6,
                        "is_critical": False,
                    },
                ]
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created (3 custom phases)
        self.assertEqual(len(subtasks), 3)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "build_app_planning")
        self.assertEqual(subtasks[0].description, "Plan the project")
        self.assertEqual(subtasks[0].agent_type, "project_planner")
        self.assertEqual(subtasks[0].parameters, {"timeline": "2 weeks"})
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])
        self.assertEqual(subtasks[0].complexity, 0.5)
        self.assertTrue(subtasks[0].is_critical)

        self.assertEqual(subtasks[1].name, "build_app_coding")
        self.assertEqual(subtasks[1].description, "Write the code")
        self.assertEqual(subtasks[1].agent_type, "coder")
        self.assertEqual(subtasks[1].parameters, {"language": "Swift"})
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [subtasks[0].id])
        self.assertEqual(subtasks[1].complexity, 0.8)
        self.assertTrue(subtasks[1].is_critical)

        self.assertEqual(subtasks[2].name, "build_app_review")
        self.assertEqual(subtasks[2].description, "Review the code")
        self.assertEqual(subtasks[2].agent_type, "reviewer")
        self.assertEqual(subtasks[2].parameters, {"standards": "company_guidelines"})
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [subtasks[1].id])
        self.assertEqual(subtasks[2].complexity, 0.6)
        self.assertFalse(subtasks[2].is_critical)


class TestDataAnalysisDecompositionStrategy(unittest.TestCase):
    """Tests for the DataAnalysisDecompositionStrategy."""

    def test_decompose(self):
        """Test decomposing a task into data analysis phases."""
        strategy = DataAnalysisDecompositionStrategy()

        # Create a complex task
        task = ComplexTask(
            name="analyze_sales",
            description="Analyze sales data for Q2 2023",
            agent_type="data_manager",
            parameters={},
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created (5 standard phases)
        self.assertEqual(len(subtasks), 5)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "analyze_sales_data_collection")
        self.assertEqual(subtasks[0].description, "Collect and gather data from various sources")
        self.assertEqual(subtasks[0].agent_type, "data_collector")
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])
        self.assertEqual(subtasks[0].complexity, 0.6)
        self.assertTrue(subtasks[0].is_critical)

        self.assertEqual(subtasks[1].name, "analyze_sales_data_cleaning")
        self.assertEqual(subtasks[1].description, "Clean and preprocess the collected data")
        self.assertEqual(subtasks[1].agent_type, "data_engineer")
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [subtasks[0].id])
        self.assertEqual(subtasks[1].complexity, 0.7)
        self.assertTrue(subtasks[1].is_critical)

        self.assertEqual(subtasks[2].name, "analyze_sales_exploratory_analysis")
        self.assertEqual(subtasks[2].description, "Perform exploratory data analysis")
        self.assertEqual(subtasks[2].agent_type, "data_analyst")
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [subtasks[1].id])
        self.assertEqual(subtasks[2].complexity, 0.8)
        self.assertTrue(subtasks[2].is_critical)

        self.assertEqual(subtasks[3].name, "analyze_sales_modeling")
        self.assertEqual(subtasks[3].description, "Build and train analytical models")
        self.assertEqual(subtasks[3].agent_type, "data_scientist")
        self.assertEqual(subtasks[3].parent_task_id, task.id)
        self.assertEqual(subtasks[3].dependencies, [subtasks[2].id])
        self.assertEqual(subtasks[3].complexity, 0.9)
        self.assertTrue(subtasks[3].is_critical)

        self.assertEqual(subtasks[4].name, "analyze_sales_reporting")
        self.assertEqual(subtasks[4].description, "Create reports and visualizations of findings")
        self.assertEqual(subtasks[4].agent_type, "data_visualizer")
        self.assertEqual(subtasks[4].parent_task_id, task.id)
        self.assertEqual(subtasks[4].dependencies, [subtasks[3].id])
        self.assertEqual(subtasks[4].complexity, 0.7)
        self.assertTrue(subtasks[4].is_critical)

    def test_decompose_with_custom_phases(self):
        """Test decomposing a task with custom data analysis phases."""
        strategy = DataAnalysisDecompositionStrategy()

        # Create a complex task with custom phases
        task = ComplexTask(
            name="analyze_sales",
            description="Analyze sales data for Q2 2023",
            agent_type="data_manager",
            parameters={
                "phases": [
                    {
                        "name": "data_extraction",
                        "description": "Extract data from the data warehouse",
                        "agent_type": "data_extractor",
                        "parameters": {"source": "data_warehouse"},
                        "complexity": 0.5,
                        "is_critical": True,
                    },
                    {
                        "name": "statistical_analysis",
                        "description": "Perform statistical analysis on the data",
                        "agent_type": "statistician",
                        "parameters": {"methods": ["regression", "anova"]},
                        "complexity": 0.8,
                        "is_critical": True,
                    },
                    {
                        "name": "presentation",
                        "description": "Present findings to stakeholders",
                        "agent_type": "presenter",
                        "parameters": {"format": "slides"},
                        "complexity": 0.6,
                        "is_critical": False,
                    },
                ]
            },
        )

        # Decompose the task
        subtasks = strategy.decompose(task)

        # Check that the correct number of subtasks were created (3 custom phases)
        self.assertEqual(len(subtasks), 3)

        # Check that the subtasks have the correct properties
        self.assertEqual(subtasks[0].name, "analyze_sales_data_extraction")
        self.assertEqual(subtasks[0].description, "Extract data from the data warehouse")
        self.assertEqual(subtasks[0].agent_type, "data_extractor")
        self.assertEqual(subtasks[0].parameters, {"source": "data_warehouse"})
        self.assertEqual(subtasks[0].parent_task_id, task.id)
        self.assertEqual(subtasks[0].dependencies, [])
        self.assertEqual(subtasks[0].complexity, 0.5)
        self.assertTrue(subtasks[0].is_critical)

        self.assertEqual(subtasks[1].name, "analyze_sales_statistical_analysis")
        self.assertEqual(subtasks[1].description, "Perform statistical analysis on the data")
        self.assertEqual(subtasks[1].agent_type, "statistician")
        self.assertEqual(subtasks[1].parameters, {"methods": ["regression", "anova"]})
        self.assertEqual(subtasks[1].parent_task_id, task.id)
        self.assertEqual(subtasks[1].dependencies, [subtasks[0].id])
        self.assertEqual(subtasks[1].complexity, 0.8)
        self.assertTrue(subtasks[1].is_critical)

        self.assertEqual(subtasks[2].name, "analyze_sales_presentation")
        self.assertEqual(subtasks[2].description, "Present findings to stakeholders")
        self.assertEqual(subtasks[2].agent_type, "presenter")
        self.assertEqual(subtasks[2].parameters, {"format": "slides"})
        self.assertEqual(subtasks[2].parent_task_id, task.id)
        self.assertEqual(subtasks[2].dependencies, [subtasks[1].id])
        self.assertEqual(subtasks[2].complexity, 0.6)
        self.assertFalse(subtasks[2].is_critical)


if __name__ == "__main__":
    unittest.main()
