#!/usr/bin/env python3
"""
Simple test file focused on just the core agentic_kernel workflow functionality.
"""
import pytest
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Define test models
class Task:
    """Simple Task model for testing."""
    def __init__(self, name, description="", agent_type="", parameters=None):
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.parameters = parameters or {}
        self.result = None

class Step:
    """Step in a workflow."""
    def __init__(self, task, dependencies=None, condition=None):
        self.task = task
        self.dependencies = dependencies or []
        self.condition = condition

class MockAgent:
    """Mock agent for testing."""
    def __init__(self, name, success=True, delay=0):
        self.name = name
        self.success = success
        self.delay = delay
        
    async def execute_task(self, task):
        """Execute a task with configurable behavior."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if not self.success:
            task.result = {"status": "error", "message": f"Failed to execute {task.name}"}
            return task.result
        
        # Set result with additional context data for condition testing
        result = {
            "status": "success", 
            "message": f"Executed {task.name}", 
            "context_value": True
        }
        task.result = result
        return result

class Orchestrator:
    """Simple workflow orchestrator."""
    def __init__(self):
        self.agents = {}
        self.logger = logging.getLogger("orchestrator")
        
    def register_agent(self, agent_type, agent):
        """Register an agent."""
        self.agents[agent_type] = agent
        
    async def execute_workflow(self, workflow):
        """Execute a workflow of interdependent steps.
        
        Args:
            workflow: List of Step objects
            
        Returns:
            dict: Execution result with metrics
        """
        start_time = asyncio.get_event_loop().time()
        
        # Tasks and their states
        pending = {step.task.name: step for step in workflow}
        completed = []
        failed = []
        skipped = []
        
        # Track dependencies
        while pending:
            # Find executable steps (all dependencies satisfied)
            executable = []
            for name, step in list(pending.items()):
                if all(dep in completed for dep in step.dependencies):
                    # Check if condition is met
                    if step.condition:
                        try:
                            # Build context from dependencies
                            context = {}
                            for dep_name in step.dependencies:
                                dep_task = next((s.task for s in workflow if s.task.name == dep_name), None)
                                if dep_task and dep_task.result:
                                    context.update(dep_task.result)
                            
                            # Log for debugging
                            self.logger.info(f"Evaluating condition '{step.condition}' with context: {context}")
                            
                            # Evaluate condition
                            if not eval(step.condition, {"__builtins__": {}}, context):
                                # Skip this step - condition not met
                                self.logger.info(f"Skipping {name}: condition not met")
                                skipped.append(name)
                                del pending[name]
                                continue
                        except Exception as e:
                            self.logger.error(f"Error evaluating condition: {e}")
                            # If condition evaluation fails, skip step
                            skipped.append(name)
                            del pending[name]
                            continue
                    
                    executable.append(step)
            
            if not executable:
                # No more executable steps but still have pending
                if pending:
                    self.logger.warning(f"Deadlock detected: {len(pending)} steps cannot be executed")
                    failed.extend(pending.keys())
                    pending.clear()
                break
            
            # Execute steps in parallel
            tasks = []
            for step in executable:
                # Remove from pending
                del pending[step.task.name]
                
                # Only execute if we have a registered agent
                agent = self.agents.get(step.task.agent_type)
                if not agent:
                    self.logger.error(f"No agent for type: {step.task.agent_type}")
                    failed.append(step.task.name)
                    continue
                
                # Queue for execution
                self.logger.info(f"Executing: {step.task.name}")
                tasks.append(self._execute_step(agent, step))
            
            # Wait for all executions to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for step, result in zip(executable, results):
                    name = step.task.name
                    if isinstance(result, Exception):
                        self.logger.error(f"Step failed with exception: {result}")
                        failed.append(name)
                    elif isinstance(result, dict) and result.get("status") == "success":
                        completed.append(name)
                    else:
                        failed.append(name)
        
        # Calculate metrics
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Determine status
        if len(completed) + len(skipped) == len(workflow):
            status = "success"
        elif completed:
            status = "partial_success"
        else:
            status = "failure"
            
        # Prepare result
        result = {
            "status": status,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "metrics": {
                "execution_time": execution_time,
                "success_rate": len(completed) / len(workflow) if workflow else 0
            }
        }
        
        return result
    
    async def _execute_step(self, agent, step):
        """Execute a single step with an agent."""
        try:
            result = await agent.execute_task(step.task)
            return result
        except Exception as e:
            self.logger.error(f"Error executing {step.task.name}: {e}")
            return {"status": "error", "message": str(e)}

# Tests

@pytest.mark.asyncio
async def test_linear_workflow():
    """Test a simple linear workflow."""
    # Create tasks
    task1 = Task(name="task1", agent_type="agent1")
    task2 = Task(name="task2", agent_type="agent1")
    
    # Create steps
    workflow = [
        Step(task=task1, dependencies=[]),
        Step(task=task2, dependencies=["task1"])
    ]
    
    # Create agent
    agent = MockAgent(name="test_agent")
    
    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent("agent1", agent)
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify
    assert result["status"] == "success"
    assert "task1" in result["completed"]
    assert "task2" in result["completed"]
    assert len(result["failed"]) == 0
    assert len(result["skipped"]) == 0

@pytest.mark.asyncio
async def test_conditional_workflow():
    """Test a workflow with conditional steps."""
    # Create tasks
    task1 = Task(name="condition_task", agent_type="agent1")
    task2 = Task(name="task_if_true", agent_type="agent1")
    task3 = Task(name="task_if_false", agent_type="agent1")
    
    # Create steps
    workflow = [
        Step(task=task1, dependencies=[]),
        Step(task=task2, dependencies=["condition_task"], condition="context_value == True"),
        Step(task=task3, dependencies=["condition_task"], condition="context_value == False")
    ]
    
    # Create agent
    agent = MockAgent(name="test_agent")
    
    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent("agent1", agent)
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Debug output
    print("\nConditional workflow result:")
    print(json.dumps(result, indent=2))
    
    # Verify
    assert result["status"] == "success"
    assert "condition_task" in result["completed"]
    assert "task_if_true" in result["completed"]
    assert "task_if_false" in result["skipped"]
    assert "task_if_false" not in result["completed"]

@pytest.mark.asyncio
async def test_failing_workflow():
    """Test a workflow with a failing step."""
    # Create tasks
    task1 = Task(name="task1", agent_type="agent1")
    task2 = Task(name="task2", agent_type="agent1")
    task3 = Task(name="task3", agent_type="agent1")
    
    # Create steps
    workflow = [
        Step(task=task1, dependencies=[]),
        Step(task=task2, dependencies=["task1"]),
        Step(task=task3, dependencies=["task2"])
    ]
    
    # Create agents
    success_agent = MockAgent(name="success_agent")
    failing_agent = MockAgent(name="failing_agent", success=False)
    
    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent("agent1", success_agent)
    
    # Override one task to use failing agent
    task2.agent_type = "agent2"
    orchestrator.register_agent("agent2", failing_agent)
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify
    assert result["status"] == "partial_success"
    assert "task1" in result["completed"]
    assert "task2" in result["failed"]
    assert "task3" in result["failed"]  # Should be marked as failed due to dependency

# Demonstration function (not pytest)
async def demo_conditional_workflow():
    """Demonstrate a workflow with conditional steps without pytest."""
    # Create tasks
    task1 = Task(name="condition_task", agent_type="agent1")
    task2 = Task(name="task_if_true", agent_type="agent1")
    task3 = Task(name="task_if_false", agent_type="agent1")
    
    # Create steps
    workflow = [
        Step(task=task1, dependencies=[]),
        Step(task=task2, dependencies=["condition_task"], condition="context_value == True"),
        Step(task=task3, dependencies=["condition_task"], condition="context_value == False")
    ]
    
    # Create agent
    agent = MockAgent(name="test_agent")
    
    # Create orchestrator
    orchestrator = Orchestrator()
    orchestrator.register_agent("agent1", agent)
    
    # Execute workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Print result
    print("\nConditional workflow result:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    # For demonstration without pytest
    if "--demo" in sys.argv:
        # Run the demo
        asyncio.run(demo_conditional_workflow())
    else:
        # Run the tests
        pytest.main(["-v", __file__]) 