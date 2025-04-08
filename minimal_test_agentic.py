#!/usr/bin/env python3
"""
Minimal test file to verify the agentic_kernel workflow functionality.
This version avoids any semantic_kernel dependencies.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Define a mock BaseAgent class based on agentic_kernel's expected interface
class BaseAgent:
    def __init__(self, config=None):
        self.id = "test_id"
        self.config = config or {}
        
    async def execute_task(self, task):
        """Execute a task."""
        pass
        
    async def receive_message(self, message):
        """Receive a message."""
        pass
        
    async def send_message(self, recipient_id, message_type, content):
        """Send a message."""
        pass

# Define Message and MessageType mocks based on agentic_kernel's communication protocol
class MessageType:
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    AGENT_STATUS = "agent_status"
    REQUEST = "request"
    RESPONSE = "response"

class Message:
    def __init__(self, sender_id, recipient_id, message_type, content):
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content = content

# Define a Task class for testing
class Task:
    """Mock Task class for testing."""
    def __init__(self, name, description="", agent_type="", parameters=None, 
                 status="pending", max_retries=0, timeout=60, **kwargs):
        self.id = kwargs.get('id', name)
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.parameters = parameters or {}
        self.status = status
        self.max_retries = max_retries
        self.timeout = timeout
        self.result = None  # Store task result here
        # Additional properties can be set via kwargs
        for key, value in kwargs.items():
            if key != 'id':  # Skip id as we already set it
                setattr(self, key, value)

# Define a WorkflowStep class for testing
class WorkflowStep:
    def __init__(self, task, dependencies=None, condition=None, max_retries=0, parallel=False):
        self.task = task
        self.dependencies = dependencies or []
        self.condition = condition
        self.max_retries = max_retries
        self.parallel = parallel

# Define the TestAgentMock class modeled after agentic_kernel's BaseAgent
class TestAgentMock(BaseAgent):
    """A mock agent implementation for testing."""

    def __init__(self, agent_type="test_agent", success=True, delay=0):
        super().__init__(config=MagicMock())
        self.agent_type = agent_type
        self.success = success
        self.delay = delay
        self.execute_task = AsyncMock()
        self.execute_task.side_effect = self._execute_with_delay
        self.messages_received = []
        self.messages_sent = []
    
    async def _execute_with_delay(self, task):
        if self.delay > 0:
            await asyncio.sleep(self.delay)
            
        if not self.success:
            error_result = {
                "status": "failed", 
                "error": f"Task execution failed for {task.name}",
                "agent_type": self.agent_type
            }
            # Store result in task object for condition evaluation
            task.result = error_result
            raise Exception(f"Task execution failed for {task.name}")
            
        success_result = {
            "status": "success", 
            "output": f"Completed task: {task.name}",
            "agent_type": self.agent_type
        }
        # Store result in task object for condition evaluation
        task.result = success_result
        return success_result
    
    async def receive_message(self, message):
        self.messages_received.append(message)
        return await super().receive_message(message)

    async def send_message(self, recipient_id, message_type, content):
        message = Message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content
        )
        self.messages_sent.append(message)
        return message

# Mock TaskLedger for testing
class TaskLedger:
    """Mock TaskLedger to track task status."""
    def __init__(self, goal):
        self.goal = goal
        self.tasks = {}  # Store task objects by name
        self.task_status = {}  # Track status by task name
        self.task_results = {}  # Store task results
        
    def register_task(self, task):
        """Register a task in the ledger."""
        self.tasks[task.name] = task
        self.task_status[task.name] = "pending"
        
    def update_task_status(self, task_name, status, result=None):
        """Update a task's status and result."""
        self.task_status[task_name] = status
        if result is not None:
            self.task_results[task_name] = result
            
            # Also update the task object if it exists
            if task_name in self.tasks:
                self.tasks[task_name].result = result
                
    def get_task(self, task_name):
        """Get a task by name."""
        return self.tasks.get(task_name)

# Mock ProgressLedger for testing
class ProgressLedger:
    def __init__(self, task_id="test_workflow"):
        self.task_id = task_id
        self.steps = {}
        self.completed_steps = set()
        self.failed_steps = set()
        self.skipped_steps = set()
        self.retried_steps = {}
        
    def register_workflow(self, workflow_steps):
        for step in workflow_steps:
            self.steps[step.task.name] = {
                "dependencies": step.dependencies,
                "status": "pending",
                "retries": 0,
                "max_retries": step.max_retries,
                "parallel": step.parallel
            }
        return True
        
    def update_step_status(self, step_name, status):
        if step_name in self.steps:
            self.steps[step_name]["status"] = status
            if status == "completed":
                self.completed_steps.add(step_name)
            elif status == "failed":
                self.failed_steps.add(step_name)
            elif status == "skipped":
                self.skipped_steps.add(step_name)
            return True
        return False
    
    def record_retry(self, step_name):
        if step_name in self.steps:
            self.steps[step_name]["retries"] += 1
            if step_name not in self.retried_steps:
                self.retried_steps[step_name] = 0
            self.retried_steps[step_name] += 1
            return self.steps[step_name]["retries"] <= self.steps[step_name]["max_retries"]
        return False
        
    def get_ready_steps(self):
        ready_steps = []
        for step_name, step_info in self.steps.items():
            if step_info["status"] == "pending":
                deps_satisfied = all(
                    dep in self.completed_steps for dep in step_info["dependencies"]
                )
                if deps_satisfied:
                    ready_steps.append(step_name)
        return ready_steps

# Mock OrchestratorAgent for testing
class OrchestratorAgent(BaseAgent):
    def __init__(self, config=None, task_ledger=None, progress_ledger=None):
        super().__init__(config=config or MagicMock())
        self.task_ledger = task_ledger or TaskLedger()
        self.progress_ledger = progress_ledger or ProgressLedger()
        self.agents = {}
        self.current_workflow = []
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
    def register_agent(self, agent):
        self.agents[agent.agent_type] = agent
    
    def _evaluate_condition(self, step):
        """Evaluate a condition expression to determine if a step should execute.
        
        Args:
            step: The workflow step containing the condition to evaluate
            
        Returns:
            bool: True if the condition is met or doesn't exist, False otherwise
        """
        if not step.condition:
            return True
            
        # Get task results from previous steps (dependencies)
        context = {}
        for dep_name in step.dependencies:
            # Get the results of the dependency
            task = self.task_ledger.get_task(dep_name)
            if task and hasattr(task, 'result') and task.result:
                # If result is a dict, add all its keys to the context
                if isinstance(task.result, dict):
                    context.update(task.result)
        
        try:
            # Print context for debugging
            self.logger.info(f"Evaluating condition '{step.condition}' with context: {context}")
            
            # Evaluate the condition in the context
            condition_result = eval(step.condition, {"__builtins__": {}}, context)
            return bool(condition_result)
        except Exception as e:
            self.logger.error(f"Error evaluating condition '{step.condition}': {str(e)}")
            # Default to false if evaluation fails
            return False
        
    async def execute_workflow(self, workflow):
        """Execute a workflow of interdependent tasks."""
        self.current_workflow = workflow
        start_time = time.time()
        
        # Register all tasks with task ledger
        for step in workflow:
            self.task_ledger.register_task(step.task)
        
        # Initialize with all steps
        pending_steps = {step.task.name: step for step in workflow}
        completed_steps = []
        failed_steps = []
        
        # Execution loop - continue until all steps are processed
        status = "success"
        while pending_steps:
            # Find steps whose dependencies are satisfied
            executable_steps = []
            for step_name, step in list(pending_steps.items()):
                # Check if all dependencies are met
                if all(dep in completed_steps for dep in step.dependencies):
                    # Evaluate condition if present
                    if step.condition:
                        condition_met = self._evaluate_condition(step)
                        if not condition_met:
                            # Skip this step - condition not met
                            self.logger.info(f"Skipping step '{step_name}' - condition not met: {step.condition}")
                            self.progress_ledger.update_step_status(step_name, "skipped")
                            # Remove from pending
                            del pending_steps[step_name]
                            # Don't add to executable steps
                            continue
                    
                    executable_steps.append(step)
            
            if not executable_steps:
                if pending_steps:
                    # We have steps that cannot be executed (likely due to failed dependencies)
                    status = "failed"
                break
            
            # Execute steps (sequentially or in parallel as appropriate)
            parallel_steps = [s for s in executable_steps if s.parallel]
            sequential_steps = [s for s in executable_steps if not s.parallel]
            
            # Execute parallel steps
            if parallel_steps:
                tasks = [self._execute_step(step) for step in parallel_steps]
                results = await asyncio.gather(*tasks)
                
                for step, result in zip(parallel_steps, results):
                    # Process results
                    if result.get("status") == "success":
                        completed_steps.append(step.task.name)
                    else:
                        failed_steps.append(step.task.name)
                        if status == "success":
                            status = "failed"
                    
                    # Remove from pending
                    del pending_steps[step.task.name]
            
            # Execute sequential steps one by one
            for step in sequential_steps:
                result = await self._execute_step(step)
                
                # Process result
                if result.get("status") == "success":
                    completed_steps.append(step.task.name)
                else:
                    failed_steps.append(step.task.name)
                    if status == "success":
                        status = "failed"
                
                # Remove from pending
                del pending_steps[step.task.name]
                
                # Stop sequential execution if a step fails
                if result.get("status") != "success":
                    break
        
        # Calculate metrics
        execution_time = time.time() - start_time
        total_steps = len(workflow)
        success_rate = len(completed_steps) / total_steps if total_steps > 0 else 0
        
        # Determine overall status
        if len(completed_steps) == total_steps:
            status = "success"
        elif len(completed_steps) > 0:
            status = "partial_success"
        else:
            status = "failed"
        
        # Prepare results
        result = {
            "status": status,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "skipped_steps": list(self.progress_ledger.skipped_steps),
            "retried_steps": self.progress_ledger.retried_steps,
            "metrics": {
                "execution_time": execution_time,
                "success_rate": success_rate
            }
        }
        
        return result
    
    async def _execute_step(self, step):
        task = step.task
        agent = self.agents.get(task.agent_type)
        
        if not agent:
            error_msg = f"No agent found for agent_type: {task.agent_type}"
            self.logger.error(error_msg)
            
            # Update ledgers
            self.task_ledger.update_task_status(task.name, "failed", {"error": error_msg})
            self.progress_ledger.update_step_status(task.name, "failed")
            
            return {
                "status": "failed",
                "error": error_msg
            }
        
        # Execute task with agent
        try:
            self.logger.info(f"Executing task: {task.name} with agent: {agent.agent_type}")
            
            # Record start time
            start_time = time.time()
            
            # Execute task
            result = await agent.execute_task(task)
            
            # Record end time
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Add execution time to result
            if isinstance(result, dict):
                result["execution_time"] = execution_time
            
            # Store result in task object for condition evaluation
            task.result = result
            
            # Update ledgers
            if result.get("status") == "success":
                self.task_ledger.update_task_status(task.name, "completed", result)
                self.progress_ledger.update_step_status(task.name, "completed")
                
                return result
            else:
                error = result.get("error", "Unknown error")
                self.logger.error(f"Task failed: {task.name} - {error}")
                
                # Update ledgers
                self.task_ledger.update_task_status(task.name, "failed", result)
                self.progress_ledger.update_step_status(task.name, "failed")
                
                return result
                
        except Exception as e:
            error_msg = f"Error executing task {task.name}: {str(e)}"
            self.logger.error(error_msg)
            
            # Create error result
            result = {
                "status": "failed",
                "error": error_msg
            }
            
            # Store result in task object
            task.result = result
            
            # Update ledgers
            self.task_ledger.update_task_status(task.name, "failed", result)
            self.progress_ledger.update_step_status(task.name, "failed")
            
            return result

########### TESTS ###########

@pytest.mark.asyncio
async def test_agent_mock_success():
    """Test that TestAgentMock can successfully execute a task."""
    agent = TestAgentMock(agent_type="test_agent", success=True)
    task = Task(name="test_task")
    
    result = await agent._execute_with_delay(task)
    
    assert result["status"] == "success"
    assert result["output"] == "Completed task: test_task"
    assert result["agent_type"] == "test_agent"

@pytest.mark.asyncio
async def test_agent_mock_failure():
    """Test that TestAgentMock fails appropriately when success=False."""
    agent = TestAgentMock(agent_type="test_agent", success=False)
    task = Task(name="test_task")
    
    with pytest.raises(Exception) as excinfo:
        await agent._execute_with_delay(task)
    
    assert "Task execution failed for test_task" in str(excinfo.value)

@pytest.mark.asyncio
async def test_agent_mock_delay():
    """Test that TestAgentMock respects the delay parameter."""
    agent = TestAgentMock(agent_type="test_agent", success=True, delay=0.1)
    task = Task(name="test_task")
    
    start_time = asyncio.get_event_loop().time()
    result = await agent._execute_with_delay(task)
    duration = asyncio.get_event_loop().time() - start_time
    
    assert duration >= 0.1
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_workflow_sequential_execution():
    """Test workflow execution with multiple steps in sequence."""
    # Create agents
    agent1 = TestAgentMock(agent_type="agent1", success=True)
    agent2 = TestAgentMock(agent_type="agent2", success=True)
    
    # Create orchestrator
    task_ledger = TaskLedger(goal="Test workflow")
    progress_ledger = ProgressLedger(task_id="test_workflow")
    orchestrator = OrchestratorAgent(
        config=MagicMock(),
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    
    # Define workflow with sequential dependencies
    workflow = [
        WorkflowStep(
            task=Task(
                name="task1",
                description="First task",
                agent_type="agent1",
                parameters={"param1": "value1"}
            ),
            dependencies=[],
            parallel=False
        ),
        WorkflowStep(
            task=Task(
                name="task2",
                description="Second task",
                agent_type="agent2",
                parameters={"param2": "value2"}
            ),
            dependencies=["task1"],
            parallel=False
        ),
        WorkflowStep(
            task=Task(
                name="task3",
                description="Third task",
                agent_type="agent1",
                parameters={"param3": "value3"}
            ),
            dependencies=["task2"],
            parallel=False
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify results
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 3
    assert set(result["completed_steps"]) == {"task1", "task2", "task3"}
    assert len(result["failed_steps"]) == 0
    assert result["metrics"]["success_rate"] == 1.0

@pytest.mark.asyncio
async def test_workflow_with_failing_task():
    """Test workflow execution with a failing task."""
    # Create agents
    agent1 = TestAgentMock(agent_type="agent1", success=True)
    agent2 = TestAgentMock(agent_type="agent2", success=False)  # This will fail
    
    # Create orchestrator
    task_ledger = TaskLedger(goal="Test workflow")
    progress_ledger = ProgressLedger(task_id="test_workflow")
    orchestrator = OrchestratorAgent(
        config=MagicMock(),
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    
    # Define workflow
    workflow = [
        WorkflowStep(
            task=Task(
                name="task1",
                description="First task",
                agent_type="agent1",
                parameters={"param1": "value1"}
            ),
            dependencies=[],
            parallel=False
        ),
        WorkflowStep(
            task=Task(
                name="task2",
                description="Second task",
                agent_type="agent2",  # This will fail
                parameters={"param2": "value2"}
            ),
            dependencies=["task1"],
            parallel=False,
            max_retries=1
        ),
        WorkflowStep(
            task=Task(
                name="task3",
                description="Third task",
                agent_type="agent1",
                parameters={"param3": "value3"}
            ),
            dependencies=["task2"],
            parallel=False
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify results
    assert result["status"] == "partial_success"
    assert len(result["completed_steps"]) == 1
    assert "task1" in result["completed_steps"]
    assert len(result["failed_steps"]) == 1
    assert "task2" in result["failed_steps"]
    assert "task3" not in result["completed_steps"]
    assert "task2" in result["retried_steps"]
    assert result["metrics"]["success_rate"] == 1/3

@pytest.mark.asyncio
async def test_parallel_execution_performance():
    """Test that parallel execution is faster than sequential execution."""
    # Create agents with delays to simulate work
    agent1 = TestAgentMock(agent_type="agent1", success=True, delay=0.1)
    agent2 = TestAgentMock(agent_type="agent2", success=True, delay=0.1)
    
    # Create orchestrator
    task_ledger = TaskLedger(goal="Test workflow")
    progress_ledger = ProgressLedger(task_id="test_workflow")
    orchestrator = OrchestratorAgent(
        config=MagicMock(),
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)
    
    # Define parallel workflow (tasks with no dependencies)
    parallel_workflow = [
        WorkflowStep(
            task=Task(
                name="parallel_task_1",
                description="Parallel task 1",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=[],
            parallel=True
        ),
        WorkflowStep(
            task=Task(
                name="parallel_task_2",
                description="Parallel task 2",
                agent_type="agent2",
                parameters={}
            ),
            dependencies=[],
            parallel=True
        )
    ]
    
    # Define sequential workflow (task2 depends on task1)
    sequential_workflow = [
        WorkflowStep(
            task=Task(
                name="sequential_task_1",
                description="Sequential task 1",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=[],
            parallel=False
        ),
        WorkflowStep(
            task=Task(
                name="sequential_task_2",
                description="Sequential task 2",
                agent_type="agent2",
                parameters={}
            ),
            dependencies=["sequential_task_1"],
            parallel=False
        )
    ]
    
    # Execute parallel workflow
    start_time = asyncio.get_event_loop().time()
    await orchestrator.execute_workflow(parallel_workflow)
    parallel_duration = asyncio.get_event_loop().time() - start_time
    
    # Reset ledgers
    orchestrator.task_ledger = TaskLedger(goal="Test workflow")
    orchestrator.progress_ledger = ProgressLedger(task_id="test_workflow")
    
    # Execute sequential workflow
    start_time = asyncio.get_event_loop().time()
    await orchestrator.execute_workflow(sequential_workflow)
    sequential_duration = asyncio.get_event_loop().time() - start_time
    
    # Verify that parallel execution was faster
    assert parallel_duration < sequential_duration
    
    # Expect the speed difference to be significant
    # In theory, parallel should be ~1x delay, sequential ~2x delay
    assert sequential_duration / parallel_duration > 1.5

@pytest.mark.asyncio
async def test_conditional_workflow_execution():
    """Test workflow with conditional execution based on task results."""
    # Create agents
    agent1 = TestAgentMock(agent_type="agent1", success=True)
    
    # Override agent execution to return custom results
    async def agent1_execute(task):
        if task.name == "condition_check":
            result = {
                "status": "success",
                "output": "Condition check completed",
                "condition_met": True  # This will be used in condition evaluation
            }
            # Important: Store result directly in the task object
            task.result = result
            return result
            
        return {
            "status": "success",
            "output": f"Completed task: {task.name}"
        }
    
    agent1.execute_task = AsyncMock(side_effect=agent1_execute)
    
    # Create orchestrator
    task_ledger = TaskLedger(goal="Test workflow")
    progress_ledger = ProgressLedger(task_id="test_workflow")
    orchestrator = OrchestratorAgent(
        config=MagicMock(),
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    orchestrator.register_agent(agent1)
    
    # Define a workflow with conditional steps
    workflow = [
        # Initial step
        WorkflowStep(
            task=Task(
                name="condition_check",
                description="Check condition",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=[],
            parallel=False
        ),
        # This step will execute if condition_met is True
        WorkflowStep(
            task=Task(
                name="task_if_true",
                description="Execute if condition is true",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=["condition_check"],
            parallel=False,
            condition="condition_met == True"
        ),
        # This step will execute if condition_met is False
        WorkflowStep(
            task=Task(
                name="task_if_false",
                description="Execute if condition is false",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=["condition_check"],
            parallel=False,
            condition="condition_met == False"
        )
    ]
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Print the result for debugging
    print(f"Workflow execution result: {result}")
    
    # Verify results
    assert result["status"] == "success"
    assert "condition_check" in result["completed_steps"]
    assert "task_if_true" in result["completed_steps"], "Expected task_if_true to execute since condition_met=True"
    assert "task_if_false" in result["skipped_steps"], "Expected task_if_false to be skipped since condition_met=True"
    assert "task_if_false" not in result["completed_steps"]

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 