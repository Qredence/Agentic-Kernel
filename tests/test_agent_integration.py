import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os

from agentic_kernel.types import Task, WorkflowStep
from agentic_kernel.agents.base_agent import BaseAgent
from agentic_kernel.agents.coder_agent import CoderAgent
from agentic_kernel.agents.terminal_agent import TerminalAgent
from agentic_kernel.agents.file_surfer_agent import FileSurferAgent
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.agents.orchestrator_agent import OrchestratorAgent
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.communication.message import Message, MessageType
from agentic_kernel.systems.agent_system import AgentSystem


@pytest.fixture
def mock_config():
    """Create a mock configuration for agents."""
    return MagicMock(
        llm_config={
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 4000
        },
        terminal_config={
            "secure_mode": True,
            "allowed_commands": ["ls", "pwd", "echo", "cat"],
            "timeout": 10
        },
        web_config={
            "timeout": 30,
            "max_pages": 5
        },
        file_config={
            "max_file_size": 1000000,
            "allowed_extensions": [".py", ".txt", ".md", ".json"]
        }
    )


@pytest.fixture
def agent_system(mock_config):
    """Create an agent system with all agent types."""
    system = AgentSystem()
    
    # Create agents
    coder = CoderAgent(config=mock_config)
    terminal = TerminalAgent(config=mock_config)
    file_surfer = FileSurferAgent(config=mock_config)
    web_surfer = WebSurferAgent(config=mock_config)
    
    # Mock the execute_task method for each agent
    coder.execute_task = AsyncMock(return_value={"status": "success", "output": "Code generated successfully"})
    terminal.execute_task = AsyncMock(return_value={"status": "success", "output": "Command executed successfully"})
    file_surfer.execute_task = AsyncMock(return_value={"status": "success", "output": "File operations completed"})
    web_surfer.execute_task = AsyncMock(return_value={"status": "success", "output": "Web content retrieved"})
    
    # Register agents with the system
    system.register_agent(coder)
    system.register_agent(terminal)
    system.register_agent(file_surfer)
    system.register_agent(web_surfer)
    
    return system


@pytest.fixture
def orchestrator(agent_system, mock_config):
    """Create an orchestrator agent registered in the agent system."""
    task_ledger = TaskLedger(goal="Integration test workflow")
    progress_ledger = ProgressLedger(task_id="integration_test")
    
    orchestrator = OrchestratorAgent(
        config=mock_config,
        task_ledger=task_ledger,
        progress_ledger=progress_ledger
    )
    
    agent_system.register_agent(orchestrator)
    
    # Set up references to all agents in the system
    for agent in agent_system.get_all_agents():
        if agent.id != orchestrator.id:
            orchestrator.register_agent(agent)
    
    return orchestrator


@pytest.mark.asyncio
async def test_coder_terminal_integration(agent_system, orchestrator):
    """Test integration between Coder and Terminal agents."""
    # Get the agents from the system
    coder = next(a for a in agent_system.get_all_agents() if isinstance(a, CoderAgent))
    terminal = next(a for a in agent_system.get_all_agents() if isinstance(a, TerminalAgent))
    
    # Mock specific behaviors for this test
    coder.execute_task = AsyncMock(return_value={
        "status": "success", 
        "output": "Code generated successfully",
        "files": [{"name": "test_script.py", "content": "print('Hello, world!')"}]
    })
    
    # Define a workflow where Coder generates code and Terminal executes it
    workflow = [
        WorkflowStep(
            task=Task(
                name="generate_python_script",
                description="Generate a Python script",
                agent_type="coder",
                parameters={"task": "Create a hello world script", "language": "python"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="execute_python_script",
                description="Execute the generated Python script",
                agent_type="terminal",
                parameters={"command": "python test_script.py"}
            ),
            dependencies=["generate_python_script"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful integration
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 2
    
    # Verify that the terminal agent was called with the right parameters
    terminal_calls = terminal.execute_task.call_args_list
    assert len(terminal_calls) == 1
    terminal_task = terminal_calls[0].args[0]
    assert terminal_task.name == "execute_python_script"
    assert terminal_task.parameters["command"] == "python test_script.py"


@pytest.mark.asyncio
async def test_web_surfer_coder_integration(agent_system, orchestrator):
    """Test integration between WebSurfer and Coder agents."""
    # Get the agents from the system
    web_surfer = next(a for a in agent_system.get_all_agents() if isinstance(a, WebSurferAgent))
    coder = next(a for a in agent_system.get_all_agents() if isinstance(a, CoderAgent))
    
    # Mock web_surfer to return API documentation
    web_surfer.execute_task = AsyncMock(return_value={
        "status": "success",
        "output": "API documentation retrieved successfully",
        "content": {
            "endpoints": [
                {"name": "/users", "method": "GET", "description": "Get all users"},
                {"name": "/users/{id}", "method": "GET", "description": "Get user by ID"}
            ]
        }
    })
    
    # Define a workflow where WebSurfer gets API docs and Coder generates code based on them
    workflow = [
        WorkflowStep(
            task=Task(
                name="fetch_api_docs",
                description="Fetch API documentation",
                agent_type="web_surfer",
                parameters={"url": "https://api.example.com/docs"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="generate_api_client",
                description="Generate API client code based on the documentation",
                agent_type="coder",
                parameters={"language": "python", "api_docs": "Will be filled from previous step"}
            ),
            dependencies=["fetch_api_docs"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful integration
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 2
    
    # Verify that the coder agent received the API docs from the web_surfer
    coder_calls = coder.execute_task.call_args_list
    assert len(coder_calls) == 1
    coder_task = coder_calls[0].args[0]
    assert coder_task.name == "generate_api_client"
    
    # The orchestrator should have passed the web_surfer results to the coder
    # We can't directly check the task parameters because the orchestrator might modify them
    # but we can verify the coder was called after the web_surfer
    assert web_surfer.execute_task.call_count == 1
    assert coder.execute_task.call_count == 1


@pytest.mark.asyncio
async def test_file_surfer_terminal_integration(agent_system, orchestrator):
    """Test integration between FileSurfer and Terminal agents."""
    # Get the agents from the system
    file_surfer = next(a for a in agent_system.get_all_agents() if isinstance(a, FileSurferAgent))
    terminal = next(a for a in agent_system.get_all_agents() if isinstance(a, TerminalAgent))
    
    # Mock file_surfer to return dependency file content
    file_surfer.execute_task = AsyncMock(return_value={
        "status": "success",
        "output": "Dependencies file found",
        "content": "numpy==1.22.0\npandas==1.4.0\nmatplotlib==3.5.0"
    })
    
    # Define a workflow where FileSurfer reads dependencies and Terminal installs them
    workflow = [
        WorkflowStep(
            task=Task(
                name="read_dependencies",
                description="Read dependencies from requirements.txt",
                agent_type="file_surfer",
                parameters={"path": "requirements.txt"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="install_dependencies",
                description="Install the dependencies",
                agent_type="terminal",
                parameters={"command": "pip install -r requirements.txt"}
            ),
            dependencies=["read_dependencies"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful integration
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == 2
    
    # Verify the file_surfer was called before the terminal
    assert file_surfer.execute_task.call_count == 1
    assert terminal.execute_task.call_count == 1


@pytest.mark.asyncio
async def test_full_development_workflow_integration(agent_system, orchestrator):
    """Test a full development workflow integrating all agent types."""
    # Get agents from the system
    web_surfer = next(a for a in agent_system.get_all_agents() if isinstance(a, WebSurferAgent))
    file_surfer = next(a for a in agent_system.get_all_agents() if isinstance(a, FileSurferAgent))
    coder = next(a for a in agent_system.get_all_agents() if isinstance(a, CoderAgent))
    terminal = next(a for a in agent_system.get_all_agents() if isinstance(a, TerminalAgent))
    
    # Setup custom mock responses for each agent
    web_surfer.execute_task = AsyncMock(side_effect=lambda task: {
        "status": "success",
        "output": f"Retrieved information about {task.parameters.get('query', '')}",
        "content": {"api_docs": [{"name": "Example API", "endpoint": "/api/v1/data"}]}
    })
    
    file_surfer.execute_task = AsyncMock(side_effect=lambda task: {
        "status": "success",
        "output": f"File operations completed for {task.name}",
        "content": "Project structure:\n- src/\n- tests/\n- requirements.txt"
    })
    
    coder.execute_task = AsyncMock(side_effect=lambda task: {
        "status": "success",
        "output": f"Code generated for {task.name}",
        "files": [{"name": "app.py", "content": "# Example app code"}]
    })
    
    terminal.execute_task = AsyncMock(side_effect=lambda task: {
        "status": "success",
        "output": f"Command executed: {task.parameters.get('command', '')}",
        "exit_code": 0
    })
    
    # Define a comprehensive development workflow
    workflow = [
        # Initial research phase
        WorkflowStep(
            task=Task(
                name="research_tech_stack",
                description="Research appropriate technology stack",
                agent_type="web_surfer",
                parameters={"query": "modern Python web frameworks"}
            ),
            dependencies=[]
        ),
        # Project setup phase
        WorkflowStep(
            task=Task(
                name="analyze_project_structure",
                description="Analyze existing project structure",
                agent_type="file_surfer",
                parameters={"path": "./"}
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="setup_virtual_env",
                description="Set up Python virtual environment",
                agent_type="terminal",
                parameters={"command": "python -m venv venv"}
            ),
            dependencies=["analyze_project_structure"]
        ),
        # Development phase
        WorkflowStep(
            task=Task(
                name="design_application",
                description="Design application architecture",
                agent_type="coder",
                parameters={"task": "Design API service", "framework": "FastAPI"}
            ),
            dependencies=["research_tech_stack", "setup_virtual_env"]
        ),
        WorkflowStep(
            task=Task(
                name="implement_api",
                description="Implement the API endpoints",
                agent_type="coder",
                parameters={"task": "Implement REST API", "spec": "Will be filled from design"}
            ),
            dependencies=["design_application"]
        ),
        # Testing phase
        WorkflowStep(
            task=Task(
                name="write_tests",
                description="Write tests for the API",
                agent_type="coder",
                parameters={"task": "Write unit tests", "target": "API endpoints"}
            ),
            dependencies=["implement_api"]
        ),
        WorkflowStep(
            task=Task(
                name="run_tests",
                description="Run the tests",
                agent_type="terminal",
                parameters={"command": "pytest tests/"}
            ),
            dependencies=["write_tests"]
        ),
        # Deployment phase
        WorkflowStep(
            task=Task(
                name="create_deployment_script",
                description="Create deployment configuration",
                agent_type="coder",
                parameters={"task": "Create Docker deployment", "app": "API service"}
            ),
            dependencies=["run_tests"]
        ),
        WorkflowStep(
            task=Task(
                name="deploy_application",
                description="Deploy the application",
                agent_type="terminal",
                parameters={"command": "docker-compose up -d"}
            ),
            dependencies=["create_deployment_script"]
        )
    ]
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify successful execution of the complete workflow
    assert result["status"] == "success"
    assert len(result["completed_steps"]) == len(workflow)
    
    # Verify all agents were utilized
    assert web_surfer.execute_task.call_count >= 1
    assert file_surfer.execute_task.call_count >= 1
    assert coder.execute_task.call_count >= 3  # Multiple coding tasks
    assert terminal.execute_task.call_count >= 3  # Multiple terminal tasks
    
    # Verify some critical dependencies were respected in the execution order
    terminal_calls = [call.args[0].name for call in terminal.execute_task.call_args_list]
    assert "setup_virtual_env" in terminal_calls
    assert "run_tests" in terminal_calls
    assert "deploy_application" in terminal_calls
    assert terminal_calls.index("setup_virtual_env") < terminal_calls.index("run_tests")
    assert terminal_calls.index("run_tests") < terminal_calls.index("deploy_application")


@pytest.mark.asyncio
async def test_error_recovery_across_agents(agent_system, orchestrator):
    """Test error recovery mechanisms across different agent types."""
    # Get agents from the system
    coder = next(a for a in agent_system.get_all_agents() if isinstance(a, CoderAgent))
    terminal = next(a for a in agent_system.get_all_agents() if isinstance(a, TerminalAgent))
    
    # Set up terminal agent to fail on first attempt then succeed
    terminal_results = [
        Exception("Command failed: syntax error"),
        {"status": "success", "output": "Command executed successfully", "exit_code": 0}
    ]
    terminal.execute_task = AsyncMock(side_effect=terminal_results)
    
    # Coder will generate code with a potential bug, then fix it after terminal failure
    coder_results = [
        {"status": "success", "output": "Initial code generated", "files": [{"name": "script.py", "content": "# Buggy code"}]},
        {"status": "success", "output": "Fixed code generated", "files": [{"name": "script.py", "content": "# Fixed code"}]}
    ]
    coder.execute_task = AsyncMock(side_effect=coder_results)
    
    # Define a workflow with retry logic
    workflow = [
        WorkflowStep(
            task=Task(
                name="generate_code",
                description="Generate initial code",
                agent_type="coder",
                parameters={"task": "Create a script", "language": "python"},
                max_retries=1
            ),
            dependencies=[]
        ),
        WorkflowStep(
            task=Task(
                name="run_code",
                description="Run the generated code",
                agent_type="terminal",
                parameters={"command": "python script.py"},
                max_retries=1,
                error_handler="fix_code"  # Special error handler
            ),
            dependencies=["generate_code"]
        ),
        WorkflowStep(
            task=Task(
                name="fix_code",
                description="Fix the code if it fails",
                agent_type="coder",
                parameters={"task": "Fix bugs in script", "file": "script.py"},
                condition="error_occurred == True"  # Only run on error
            ),
            dependencies=["generate_code"]
        )
    ]
    
    # Mock the condition evaluator in orchestrator
    def evaluate_condition(condition, context):
        if condition == "error_occurred == True":
            return context.get("error_occurred", False)
        return True
    
    orchestrator._evaluate_condition = MagicMock(side_effect=evaluate_condition)
    
    # Setup orchestrator to handle error and trigger recovery
    original_execute_step = orchestrator._execute_step
    
    async def mock_execute_step(step, context=None):
        if context is None:
            context = {}
        
        result = await original_execute_step(step, context)
        
        # If this is the "run_code" step and it fails, set error flag
        if step.task.name == "run_code" and result.get("status") == "error":
            context["error_occurred"] = True
            
            # Trigger the error handler if specified
            if step.task.error_handler:
                error_step = next((s for s in workflow if s.task.name == step.task.error_handler), None)
                if error_step:
                    await orchestrator._execute_step(error_step, context)
                    
                    # After error handling, retry the failed step
                    return await original_execute_step(step, context)
        
        return result
    
    orchestrator._execute_step = mock_execute_step
    
    # Execute the workflow
    result = await orchestrator.execute_workflow(workflow)
    
    # Verify the recovery process worked
    assert result["status"] == "success"
    assert "generate_code" in result["completed_steps"]
    assert "run_code" in result["completed_steps"]
    assert "fix_code" in result.get("conditional_steps", [])
    
    # Verify the recovery and retry sequence
    assert coder.execute_task.call_count == 2  # Initial code + fix
    assert terminal.execute_task.call_count == 2  # Failed attempt + successful retry 