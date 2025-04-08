"""Tests for the workflow versioning and history functionality."""

import pytest
import os
import json
from datetime import datetime
from typing import List, Dict, Any

from src.agentic_kernel.orchestrator.workflow_history import (
    WorkflowHistory,
    WorkflowVersion,
    ExecutionRecord,
)
from src.agentic_kernel.types import Task, WorkflowStep


@pytest.fixture
def test_steps() -> List[WorkflowStep]:
    """Create test workflow steps."""
    return [
        WorkflowStep(
            task=Task(
                name="step1",
                description="First step",
                agent_type="test",
                parameters={"param1": "value1"},
            ),
            dependencies=[],
        ),
        WorkflowStep(
            task=Task(
                name="step2",
                description="Second step",
                agent_type="test",
                parameters={"param2": "value2"},
            ),
            dependencies=["step1"],
        ),
        WorkflowStep(
            task=Task(
                name="step3",
                description="Third step",
                agent_type="test",
                parameters={"param3": "value3"},
            ),
            dependencies=["step2"],
        ),
    ]


@pytest.fixture
def modified_steps(test_steps) -> List[WorkflowStep]:
    """Create modified workflow steps."""
    # Copy original steps
    steps = [
        WorkflowStep(
            task=Task(
                name=step.task.name,
                description=step.task.description,
                agent_type=step.task.agent_type,
                parameters=step.task.parameters.copy(),
            ),
            dependencies=step.dependencies.copy(),
            parallel=step.parallel,
            condition=step.condition,
        )
        for step in test_steps
    ]
    
    # Modify step2 parameters
    steps[1].task.parameters["param2"] = "modified"
    
    # Add a new step
    steps.append(
        WorkflowStep(
            task=Task(
                name="step4",
                description="Fourth step",
                agent_type="test",
                parameters={"param4": "value4"},
            ),
            dependencies=["step3"],
        )
    )
    
    return steps


@pytest.fixture
async def workflow_history() -> WorkflowHistory:
    """Create a test workflow history."""
    return WorkflowHistory()


@pytest.mark.asyncio
async def test_create_workflow(workflow_history, test_steps):
    """Test creating a new workflow with initial version."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Verify workflow was created
    assert workflow_id in workflow_history.workflows
    assert workflow_id in workflow_history.versions
    
    # Verify workflow metadata
    workflow = workflow_history.workflows[workflow_id]
    assert workflow["name"] == "Test Workflow"
    assert workflow["description"] == "A test workflow"
    assert workflow["created_by"] == "test_user"
    assert workflow["current_version_id"] == version_id
    
    # Verify version was created
    versions = workflow_history.versions[workflow_id]
    assert len(versions) == 1
    assert versions[0].version_id == version_id
    assert versions[0].workflow_id == workflow_id
    assert len(versions[0].steps) == len(test_steps)


@pytest.mark.asyncio
async def test_create_version(workflow_history, test_steps, modified_steps):
    """Test creating a new version of a workflow."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Create a new version
    new_version = await workflow_history.create_version(
        workflow_id=workflow_id,
        steps=modified_steps,
        created_by="test_user",
        description="Modified version",
    )
    
    # Verify new version was created
    versions = workflow_history.versions[workflow_id]
    assert len(versions) == 2
    assert new_version.version_id in [v.version_id for v in versions]
    assert new_version.parent_version_id == version_id
    assert new_version.description == "Modified version"
    assert len(new_version.steps) == len(modified_steps)
    
    # Verify current version was updated
    assert workflow_history.workflows[workflow_id]["current_version_id"] == new_version.version_id


@pytest.mark.asyncio
async def test_get_version(workflow_history, test_steps, modified_steps):
    """Test retrieving a specific workflow version."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Create a new version
    new_version = await workflow_history.create_version(
        workflow_id=workflow_id,
        steps=modified_steps,
        created_by="test_user",
        description="Modified version",
    )
    
    # Get the first version
    first_version = await workflow_history.get_version(workflow_id, version_id)
    assert first_version is not None
    assert first_version.version_id == version_id
    assert len(first_version.steps) == len(test_steps)
    
    # Get the second version
    second_version = await workflow_history.get_version(workflow_id, new_version.version_id)
    assert second_version is not None
    assert second_version.version_id == new_version.version_id
    assert len(second_version.steps) == len(modified_steps)
    
    # Get current version (should be the second version)
    current_version = await workflow_history.get_version(workflow_id)
    assert current_version is not None
    assert current_version.version_id == new_version.version_id


@pytest.mark.asyncio
async def test_get_version_history(workflow_history, test_steps, modified_steps):
    """Test retrieving version history for a workflow."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Create two more versions
    version2 = await workflow_history.create_version(
        workflow_id=workflow_id,
        steps=modified_steps,
        created_by="test_user",
        description="Modified version",
    )
    
    version3 = await workflow_history.create_version(
        workflow_id=workflow_id,
        steps=modified_steps,
        created_by="test_user2",
        description="Another modified version",
    )
    
    # Get version history
    history = await workflow_history.get_version_history(workflow_id)
    
    # Verify history structure
    assert len(history) == 3
    assert history[0]["version_id"] == version_id
    assert history[1]["version_id"] == version2.version_id
    assert history[2]["version_id"] == version3.version_id
    
    # Verify history metadata
    assert history[0]["created_by"] == "test_user"
    assert history[0]["description"] == "Initial version"
    assert history[0]["is_current"] is False
    
    assert history[2]["created_by"] == "test_user2"
    assert history[2]["description"] == "Another modified version"
    assert history[2]["is_current"] is True


@pytest.mark.asyncio
async def test_compare_versions(workflow_history, test_steps, modified_steps):
    """Test comparing two workflow versions."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Create a new version
    new_version = await workflow_history.create_version(
        workflow_id=workflow_id,
        steps=modified_steps,
        created_by="test_user",
        description="Modified version",
    )
    
    # Compare versions
    comparison = await workflow_history.compare_versions(
        workflow_id, version_id, new_version.version_id
    )
    
    # Verify comparison structure
    assert comparison["workflow_id"] == workflow_id
    assert comparison["version1"]["id"] == version_id
    assert comparison["version2"]["id"] == new_version.version_id
    
    # Verify differences
    differences = comparison["differences"]
    assert "step4" in differences["added_steps"]
    assert "step2" in differences["modified_steps"]
    assert len(differences["removed_steps"]) == 0
    assert differences["total_changes"] == 2


@pytest.mark.asyncio
async def test_execute_workflow_tracking(workflow_history, test_steps):
    """Test tracking workflow execution."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Start execution
    execution = await workflow_history.start_execution(workflow_id, version_id)
    execution_id = execution.execution_id
    
    # Record step results
    await workflow_history.record_step_result(
        execution_id=execution_id,
        step_name="step1",
        result={"status": "success", "output": {"result": "step1_output"}},
    )
    
    await workflow_history.record_step_result(
        execution_id=execution_id,
        step_name="step2",
        result={"status": "success", "output": {"result": "step2_output"}},
    )
    
    await workflow_history.record_step_result(
        execution_id=execution_id,
        step_name="step3",
        result={"status": "failed", "error": "Step 3 failed"},
    )
    
    # Complete execution
    updated_execution = await workflow_history.complete_execution(
        execution_id=execution_id,
        status="partial_success",
    )
    
    # Verify execution record
    assert updated_execution is not None
    assert updated_execution.status == "partial_success"
    assert updated_execution.start_time is not None
    assert updated_execution.end_time is not None
    assert len(updated_execution.step_results) == 3
    assert len(updated_execution.errors) == 1
    assert updated_execution.errors[0]["step"] == "step3"
    
    # Verify metrics
    assert updated_execution.metrics["success_rate"] == 2/3
    assert updated_execution.metrics["execution_time"] > 0


@pytest.mark.asyncio
async def test_get_execution_history(workflow_history, test_steps):
    """Test retrieving execution history for a workflow."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Run three executions
    for i in range(3):
        execution = await workflow_history.start_execution(workflow_id, version_id)
        execution_id = execution.execution_id
        
        # Record step results
        for step in test_steps:
            status = "success" if i < 2 else "failed" if step.task.name == "step3" else "success"
            result = {
                "status": status,
                "output": {"result": f"{step.task.name}_output_{i}"},
            }
            if status == "failed":
                result = {"status": "failed", "error": f"{step.task.name} failed"}
                
            await workflow_history.record_step_result(
                execution_id=execution_id,
                step_name=step.task.name,
                result=result,
            )
            
        # Complete execution
        final_status = "success" if i < 2 else "partial_success"
        await workflow_history.complete_execution(
            execution_id=execution_id,
            status=final_status,
        )
    
    # Get execution history
    history = await workflow_history.get_execution_history(workflow_id)
    
    # Verify history structure
    assert len(history) == 3
    assert history[0]["status"] == "partial_success"  # Most recent first
    assert history[1]["status"] == "success"
    assert history[2]["status"] == "success"
    assert all("execution_id" in execution for execution in history)
    assert all("metrics" in execution for execution in history)


@pytest.mark.asyncio
async def test_persist_and_load_history(workflow_history, test_steps, tmp_path):
    """Test persisting and loading workflow history."""
    # Create a workflow
    workflow_id, version_id = await workflow_history.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        creator="test_user",
        steps=test_steps,
    )
    
    # Run an execution
    execution = await workflow_history.start_execution(workflow_id, version_id)
    execution_id = execution.execution_id
    
    # Record step results
    for step in test_steps:
        result = {"status": "success", "output": {"result": f"{step.task.name}_output"}}
        await workflow_history.record_step_result(
            execution_id=execution_id,
            step_name=step.task.name,
            result=result,
        )
    
    # Complete execution
    await workflow_history.complete_execution(
        execution_id=execution_id,
        status="success",
    )
    
    # Create a storage file
    storage_path = os.path.join(tmp_path, "workflow_history.json")
    
    # Persist history
    await workflow_history.persist_history(storage_path)
    
    # Verify file exists
    assert os.path.exists(storage_path)
    
    # Load history
    loaded_history = await WorkflowHistory.load_history(storage_path)
    
    # Verify loaded history
    assert workflow_id in loaded_history.workflows
    assert workflow_id in loaded_history.versions
    assert workflow_id in loaded_history.executions
    
    # Compare with original history
    assert len(loaded_history.versions[workflow_id]) == len(workflow_history.versions[workflow_id])
    assert len(loaded_history.executions[workflow_id]) == len(workflow_history.executions[workflow_id])
    
    # Verify version details
    original_version = workflow_history.versions[workflow_id][0]
    loaded_version = loaded_history.versions[workflow_id][0]
    assert loaded_version.version_id == original_version.version_id
    assert loaded_version.description == original_version.description
    assert len(loaded_version.steps) == len(original_version.steps)
    
    # Verify execution details
    original_execution = workflow_history.executions[workflow_id][0]
    loaded_execution = loaded_history.executions[workflow_id][0]
    assert loaded_execution.execution_id == original_execution.execution_id
    assert loaded_execution.status == original_execution.status
    assert len(loaded_execution.step_results) == len(original_execution.step_results) 