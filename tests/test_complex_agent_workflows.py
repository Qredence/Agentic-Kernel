import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from agentic_kernel.types import Task, WorkflowStep
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.agents.coder_agent import CoderAgent
from agentic_kernel.agents.terminal_agent import TerminalAgent
from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.communication.message import Message, MessageType
from agentic_kernel.communication.protocol import CommunicationProtocol


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
        message = Message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content
        )
        self.messages_sent.append(message)
        return message


@pytest.fixture
def create_mock_agents():
    """Factory fixture to create mock agents with specified behaviors."""
    def _create_agents(agent_configs):
        agents = {}
        for agent_type, config in agent_configs.items():
            agents[agent_type] = TestAgentMock(
                agent_type=agent_type,
                success=config.get("success", True),
                delay=config.get("delay", 0)
            )
        return agents
    return _create_agents


@pytest.fixture
async def orchestrator_with_agents(create_mock_agents):
    """Create an orchestrator with configurable agents."""
    
    def _create_orchestrator(agent_configs, goal="Test complex workflow"):
        agents = create_mock_agents(agent_configs)
        
        task_ledger = TaskLedger(goal=goal)
        progress_ledger = ProgressLedger(task_id="test_complex_workflow")
        
        orchestrator = OrchestratorAgent(
            config=MagicMock(),
            task_ledger=task_ledger,
            progress_ledger=progress_ledger
        )
        
        # Register all mock agents with the orchestrator
        for agent in agents.values():
            orchestrator.register_agent(agent)
            
        return orchestrator, agents
        
    return _create_orchestrator


@pytest.mark.asyncio
async def test_complex_workflow_with_multiple_dependencies(orchestrator_with_agents):
    """Test execution of a complex workflow with multiple dependencies and branching."""
    # Create orchestrator with all agents working properly
    agent_configs = {
        "coder": {"success": True},
        "terminal": {"success": True},
        "file_surfer": {"success": True},
        "web_surfer": {"success": True}
    }
    
    orchestrator, agents = await orchestrator_with_agents(agent_configs)
    
    # Define a complex workflow with multiple dependencies
    workflow = [
        # Initialize tasks
        WorkflowStep(
            task=Task(
                name="fetch_requirements",
                description="Fetch project requirements",
                agent_type="file_surfer",
                parameters={"file_path": "requirements.txt"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="research_api",
                description="Research API documentation",
                agent_type="web_surfer",
                parameters={"url": "https://api.example.com/docs"}
            ),
            dependencies=[]
        ),
        # First level of dependent tasks
        WorkflowStep(
            task=Task(
                name="install_dependencies",
                description="Install required dependencies",
                agent_type="terminal",
                parameters={"command": "pip install -r requirements.txt"}
            ),
            dependencies=["fetch_requirements"]
        ),
        WorkflowStep(
            task=Task(
                name="design_architecture",
                description="Design system architecture",
                agent_type="coder",
                parameters={"specs": "Architecture design based on requirements"}
            ),
            dependencies=["fetch_requirements", "research_api"]
        ),
        # Final integration task
        WorkflowStep(
            task=Task(
                name="implement_integration",
                description="Implement API integration",
                agent_type="coder",
                parameters={"design": "Implementation based on architecture"}
            ),
            dependencies=["design_architecture", "install_dependencies"]
        ),
        WorkflowStep(
            task=Task(
                name="test_integration",
                description="Test the integration",
                agent_type="terminal",
                parameters={"command": "pytest tests/"}
            ),
            dependencies=["implement_integration"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful execution
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 6
    assert len(result["failed_steps"]) == 0
    
    # Verify execution order follows dependencies
    executed_tasks = [call.args[0].name for call in agents["coder"].execute_task.call_args_list]
    assert "design_architecture" in executed_tasks
    assert "implement_integration" in executed_tasks
    assert executed_tasks.index("design_architecture") < executed_tasks.index("implement_integration")
    
    # Verify metrics
    assert result["metrics"]["success_rate"] == 1.0
    assert result["metrics"]["execution_time"] > 0


@pytest.mark.asyncio
async def test_workflow_with_failing_agent(orchestrator_with_agents):
    """Test workflow execution with a failing agent and verify error propagation."""
    # Create orchestrator with one failing agent
    agent_configs = {
        "coder": {"success": True},
        "terminal": {"success": False},  # This agent will fail
        "file_surfer": {"success": True},
        "web_surfer": {"success": True}
    }
    
    orchestrator, agents = await orchestrator_with_agents(agent_configs)
    
    # Create a workflow with the failing agent in the middle
    workflow = [
        WorkflowStep(
            task=Task(
                name="fetch_code",
                description="Fetch code from repository",
                agent_type="file_surfer",
                parameters={"path": "src/"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="build_code",
                description="Build the code",
                agent_type="terminal",  # This will fail
                parameters={"command": "make build"},
                max_retries=1
            ),
            dependencies=["fetch_code"]
        ),
        WorkflowStep(
            task=Task(
                name="deploy_code",
                description="Deploy the built code",
                agent_type="terminal",
                parameters={"command": "make deploy"}
            ),
            dependencies=["build_code"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify partial success with correct failure identification
    assert result["status"] == "partial_success"
    assert "fetch_code" in result["completed_steps"]
    assert "build_code" in result["failed_steps"]
    assert "deploy_code" not in result["completed_steps"]
    assert result["metrics"]["success_rate"] < 1.0
    
    # Verify retries
    assert "build_code" in result.get("retried_steps", {})
    assert agents["terminal"].execute_task.call_count == 2  # Original + 1 retry


@pytest.mark.asyncio
async def test_inter_agent_communication(orchestrator_with_agents):
    """Test communication between agents during workflow execution."""
    # Create orchestrator with agents
    agent_configs = {
        "coder": {"success": True},
        "terminal": {"success": True},
    }
    
    orchestrator, agents = await orchestrator_with_agents(agent_configs)
    
    # Create a simple workflow
    workflow = [
        WorkflowStep(
            task=Task(
                name="generate_script",
                description="Generate a shell script",
                agent_type="coder",
                parameters={"language": "bash", "purpose": "system check"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="execute_script",
                description="Execute the generated script",
                agent_type="terminal",
                parameters={"script_path": "/tmp/check.sh"}
            ),
            dependencies=["generate_script"]
        )
    ]
    
    # Patch the communication protocol
    with patch.object(CommunicationProtocol, 'send_message', new_callable=AsyncMock) as mock_send:
        # Execute the workflow
        result = await orchestrator.execute_workflow(workflow)
        
        # Verify successful execution
        assert result["status"] == "success"
        
        # Verify communication between agents
        assert mock_send.call_count > 0
        
        # Verify message flow from coder to terminal
        coder_agent = agents["coder"]
        terminal_agent = agents["terminal"]
        
        # Check if coder sent messages
        assert len(coder_agent.messages_sent) > 0
        
        # Verify task completion message flow
        completion_messages = [
            msg for msg in coder_agent.messages_sent 
            if msg.message_type == MessageType.TASK_COMPLETE
        ]
        assert len(completion_messages) > 0


@pytest.mark.asyncio
async def test_parallel_execution_performance(orchestrator_with_agents):
    """Test performance of parallel execution compared to sequential execution."""
    # Create agents with specified delays to simulate work
    agent_configs = {
        "agent1": {"delay": 0.2},
        "agent2": {"delay": 0.2},
        "agent3": {"delay": 0.2},
        "agent4": {"delay": 0.2}
    }
    
    orchestrator, agents = await orchestrator_with_agents(agent_configs)
    
    # Define a workflow with parallel tasks
    parallel_workflow = [
        WorkflowStep(
            task=Task(
                name=f"parallel_task_{i}",
                description=f"Parallel task {i}",
                agent_type=f"agent{i}",
                parameters={}
            ),
            dependencies=[]
        )
        for i in range(1, 5)  # 4 parallel tasks
    ]
    
    # Define a sequential workflow
    sequential_workflow = [
        WorkflowStep(
            task=Task(
                name="sequential_task_1",
                description="Sequential task 1",
                agent_type="agent1",
                parameters={}
            ),
            dependencies=[]
        )
    ]
    
    # Add sequential dependencies
    for i in range(2, 5):
        sequential_workflow.append(
            WorkflowStep(
                task=Task(
                    name=f"sequential_task_{i}",
                    description=f"Sequential task {i}",
                    agent_type=f"agent{i}",
                    parameters={}
                ),
                dependencies=[f"sequential_task_{i-1}"]
            )
        )
    
    # Execute parallel workflow
    start_time = asyncio.get_event_loop().time()
    parallel_result = await orchestrator.execute_workflow(parallel_workflow)
    parallel_duration = asyncio.get_event_loop().time() - start_time
    
    # Reset agent mocks
    for agent in agents.values():
        agent.execute_task.reset_mock()
    
    # Execute sequential workflow
    start_time = asyncio.get_event_loop().time()
    sequential_result = await orchestrator.execute_workflow(sequential_workflow)
    sequential_duration = asyncio.get_event_loop().time() - start_time
    
    # Verify both workflows completed successfully
    assert parallel_result["status"] == "success"
    assert sequential_result["status"] == "success"
    
    # Verify that parallel execution was faster
    assert parallel_duration < sequential_duration
    
    # The speedup should be close to the number of agents if truly parallel
    # With added orchestration overhead, we expect it to be at least 1.5x faster
    assert sequential_duration / parallel_duration > 1.5


@pytest.mark.asyncio
async def test_conditional_workflow_execution(orchestrator_with_agents):
    """Test workflow with conditional execution paths based on previous results."""
    # Create agents
    agent_configs = {
        "file_surfer": {"success": True},
        "coder": {"success": True}
    }
    
    orchestrator, agents = await orchestrator_with_agents(agent_configs)
    
    # Override the execute method of the file_surfer agent to return specific results
    async def custom_execute(task):
        if task.name == "check_repository":
            return {
                "status": "success",
                "output": "Repository check completed",
                "has_tests": True  # This will determine the conditional path
            }
        return {
            "status": "success",
            "output": f"Completed task: {task.name}"
        }
    
    agents["file_surfer"].execute_task = AsyncMock(side_effect=custom_execute)
    
    # Define a workflow with conditional execution
    workflow = [
        # Initial step
        WorkflowStep(
            task=Task(
                name="check_repository",
                description="Check repository structure",
                agent_type="file_surfer",
                parameters={"path": "src/"}
            ),
            dependencies=[]
        ),
        # Conditional step - will only execute if tests are found
        WorkflowStep(
            task=Task(
                name="run_tests",
                description="Run existing tests",
                agent_type="coder",
                parameters={"test_path": "tests/"},
                condition="has_tests == True"  # Conditional execution
            ),
            dependencies=["check_repository"]
        ),
        # Alternative step - will execute if no tests are found
        WorkflowStep(
            task=Task(
                name="create_tests",
                description="Create new tests",
                agent_type="coder",
                parameters={"source_path": "src/"},
                condition="has_tests == False"  # Opposite condition
            ),
            dependencies=["check_repository"]
        )
    ]
    
    # Mock the condition evaluator in orchestrator
    def evaluate_condition(condition, context):
        if condition == "has_tests == True":
            return context.get("has_tests", False)
        elif condition == "has_tests == False":
            return not context.get("has_tests", False)
        return True
    
    orchestrator._evaluate_condition = MagicMock(side_effect=evaluate_condition)
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful execution
    assert result["status"] == "success"
    
    # Verify that only the appropriate conditional path was taken
    assert "check_repository" in result["completed_steps"]
    assert "run_tests" in result["completed_steps"]
    assert "create_tests" not in result["completed_steps"]
    
    # Change the condition result and test again
    async def custom_execute_no_tests(task):
        if task.name == "check_repository":
            return {
                "status": "success",
                "output": "Repository check completed",
                "has_tests": False  # Changed to False to take the other path
            }
        return {
            "status": "success",
            "output": f"Completed task: {task.name}"
        }
    
    agents["file_surfer"].execute_task = AsyncMock(side_effect=custom_execute_no_tests)
    
    # Reset agents and execute again
    for agent in agents.values():
        agent.execute_task.reset_mock()
    
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify the alternative path was taken
    assert "check_repository" in result["completed_steps"]
    assert "run_tests" not in result["completed_steps"]
    assert "create_tests" in result["completed_steps"] 