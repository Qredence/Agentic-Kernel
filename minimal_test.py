#!/usr/bin/env python3
"""
Minimal test file to verify the TestAgentMock works and can execute workflows.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Define a mock BaseAgent class to avoid importing from agentic_kernel
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

# Define a Task class for testing
class Task:
    def __init__(self, name, description="", agent_type="", parameters=None):
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.parameters = parameters or {}

# Define a WorkflowStep class for testing
class WorkflowStep:
    def __init__(self, task, dependencies=None, condition=None, max_retries=0):
        self.task = task
        self.dependencies = dependencies or []
        self.condition = condition
        self.max_retries = max_retries

# Define the TestAgentMock class (copied from test_complex_agent_workflows.py)
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
            raise Exception(f"Task execution failed for {task.name}")
            
        return {
            "status": "success", 
            "output": f"Completed task: {task.name}",
            "agent_type": self.agent_type
        }
    
    async def receive_message(self, message):
        self.messages_received.append(message)
        return await super().receive_message(message)

    async def send_message(self, recipient_id, message_type, content):
        message = {"sender_id": self.id, "recipient_id": recipient_id, "type": message_type, "content": content}
        self.messages_sent.append(message)
        return message

# Mock TaskLedger for testing
class TaskLedger:
    def __init__(self, goal="Test goal"):
        self.goal = goal
        self.tasks = {}
        
    def register_task(self, task, task_id=None):
        task_id = task_id or task.name
        self.tasks[task_id] = {"task": task, "status": "pending"}
        return task_id
        
    def update_task_status(self, task_id, status, result=None):
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = status
            self.tasks[task_id]["result"] = result
            return True
        return False

# Mock ProgressLedger for testing
class ProgressLedger:
    def __init__(self, task_id="test_workflow"):
        self.task_id = task_id
        self.steps = {}
        self.completed_steps = set()
        self.failed_steps = set()
        
    def register_workflow(self, workflow_steps):
        for step in workflow_steps:
            self.steps[step.task.name] = {
                "dependencies": step.dependencies,
                "status": "pending"
            }
        return True
        
    def update_step_status(self, step_name, status):
        if step_name in self.steps:
            self.steps[step_name]["status"] = status
            if status == "completed":
                self.completed_steps.add(step_name)
            elif status == "failed":
                self.failed_steps.add(step_name)
            return True
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
        
    def register_agent(self, agent):
        self.agents[agent.agent_type] = agent
        
    async def execute_workflow(self, workflow):
        start_time = asyncio.get_event_loop().time()
        
        # Register workflow with progress ledger
        self.progress_ledger.register_workflow(workflow)
        
        # Register all tasks with task ledger
        for step in workflow:
            self.task_ledger.register_task(step.task)
        
        # Execute workflow steps
        completed_steps = []
        failed_steps = []
        
        # Continue until all steps are processed
        while True:
            # Get steps that are ready to execute
            ready_steps = self.progress_ledger.get_ready_steps()
            
            if not ready_steps:
                # No more steps to execute
                break
                
            # Execute all ready steps in parallel
            tasks = []
            for step_name in ready_steps:
                for step in workflow:
                    if step.task.name == step_name:
                        agent_type = step.task.agent_type
                        if agent_type in self.agents:
                            self.progress_ledger.update_step_status(step_name, "executing")
                            task = asyncio.create_task(self._execute_step(step))
                            tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks)
            else:
                break
        
        # Calculate execution time
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Determine overall status
        total_steps = len(workflow)
        completed_steps = list(self.progress_ledger.completed_steps)
        failed_steps = list(self.progress_ledger.failed_steps)
        
        if len(completed_steps) == total_steps:
            status = "success"
        elif len(completed_steps) > 0:
            status = "partial_success"
        else:
            status = "failure"
            
        # Calculate success rate
        success_rate = len(completed_steps) / total_steps if total_steps > 0 else 0
        
        # Prepare results
        result = {
            "status": status,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "metrics": {
                "execution_time": execution_time,
                "success_rate": success_rate
            }
        }
        
        return result
    
    async def _execute_step(self, step):
        task = step.task
        agent = self.agents.get(task.agent_type)
        
        if agent:
            try:
                result = await agent.execute_task(task)
                self.task_ledger.update_task_status(task.name, "completed", result)
                self.progress_ledger.update_step_status(task.name, "completed")
                return result
            except Exception as e:
                self.task_ledger.update_task_status(task.name, "failed", {"error": str(e)})
                self.progress_ledger.update_step_status(task.name, "failed")
                return {"error": str(e)}
        else:
            self.progress_ledger.update_step_status(task.name, "failed")
            return {"error": f"No agent found for type: {task.agent_type}"}

# Define a simple test
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
async def test_workflow_execution():
    """Test workflow execution with multiple steps."""
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
    
    # Define workflow
    workflow = [
        WorkflowStep(
            task=Task(
                name="task1",
                description="First task",
                agent_type="agent1",
                parameters={"param1": "value1"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="task2",
                description="Second task",
                agent_type="agent2",
                parameters={"param2": "value2"}
            ),
            dependencies=["task1"]
        ),
        WorkflowStep(
            task=Task(
                name="task3",
                description="Third task",
                agent_type="agent1",
                parameters={"param3": "value3"}
            ),
            dependencies=["task2"]
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
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="task2",
                description="Second task",
                agent_type="agent2",  # This will fail
                parameters={"param2": "value2"}
            ),
            dependencies=["task1"]
        ),
        WorkflowStep(
            task=Task(
                name="task3",
                description="Third task",
                agent_type="agent1",
                parameters={"param3": "value3"}
            ),
            dependencies=["task2"]
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
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="parallel_task_2",
                description="Parallel task 2",
                agent_type="agent2",
                parameters={}
            ),
            dependencies=[]
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
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="sequential_task_2",
                description="Sequential task 2",
                agent_type="agent2",
                parameters={}
            ),
            dependencies=["sequential_task_1"]
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

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 