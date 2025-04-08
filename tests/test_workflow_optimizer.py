"""Tests for the workflow optimization functionality."""

import pytest
from datetime import datetime, timedelta
import uuid
from typing import Dict, List, Any, Optional

from src.agentic_kernel.types import Task, WorkflowStep
from src.agentic_kernel.orchestrator.workflow_optimizer import (
    WorkflowOptimizer,
    ParallelizationOptimizer,
    AgentSelectionOptimizer,
    ResourceOptimizer
)


@pytest.fixture
def sample_workflow():
    """Create a sample workflow for testing."""
    steps = []
    
    # Create a simple linear workflow
    task1 = Task(
        name="fetch_data",
        description="Fetch data from the API",
        agent_type="web_surfer",
        parameters={"url": "https://api.example.com/data"}
    )
    step1 = WorkflowStep(
        task=task1,
        dependencies=[],
        parallel=False
    )
    steps.append(step1)
    
    task2 = Task(
        name="process_data",
        description="Process the fetched data",
        agent_type="data_processor",
        parameters={"batch_size": 100, "timeout": 300}
    )
    step2 = WorkflowStep(
        task=task2,
        dependencies=["fetch_data"],
        parallel=False
    )
    steps.append(step2)
    
    task3 = Task(
        name="generate_report",
        description="Generate a report from the processed data",
        agent_type="report_generator",
        parameters={"format": "pdf"}
    )
    step3 = WorkflowStep(
        task=task3,
        dependencies=["process_data"],
        parallel=False
    )
    steps.append(step3)
    
    task4 = Task(
        name="send_notification",
        description="Send notification about the report",
        agent_type="notifier",
        parameters={"recipients": ["user@example.com"]}
    )
    step4 = WorkflowStep(
        task=task4,
        dependencies=["generate_report"],
        parallel=False
    )
    steps.append(step4)
    
    return steps


@pytest.fixture
def sample_execution_history():
    """Create sample execution history for testing."""
    # Create a few execution records with various metrics
    now = datetime.utcnow()
    
    history = []
    
    # First execution record
    history.append({
        "execution_id": str(uuid.uuid4()),
        "workflow_id": "test_workflow",
        "version_id": "v1",
        "start_time": (now - timedelta(days=2)).isoformat(),
        "end_time": (now - timedelta(days=2) + timedelta(minutes=10)).isoformat(),
        "status": "success",
        "step_results": {
            "fetch_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 60.5,
                    "agent_type": "web_surfer",
                    "agent_id": "agent1",
                    "resource_usage": {
                        "memory": 120,
                        "cpu": 30,
                        "network": 500
                    }
                }
            },
            "process_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 180.3,
                    "agent_type": "data_processor",
                    "agent_id": "agent2",
                    "resource_usage": {
                        "memory": 2200,
                        "cpu": 90,
                        "disk": 150
                    }
                }
            },
            "generate_report": {
                "status": "success",
                "metrics": {
                    "execution_time": 120.7,
                    "agent_type": "report_generator",
                    "agent_id": "agent3",
                    "resource_usage": {
                        "memory": 450,
                        "cpu": 60,
                        "disk": 200
                    }
                }
            },
            "send_notification": {
                "status": "success",
                "metrics": {
                    "execution_time": 15.2,
                    "agent_type": "notifier",
                    "agent_id": "agent4",
                    "resource_usage": {
                        "memory": 80,
                        "cpu": 10,
                        "network": 50
                    }
                }
            }
        },
        "metrics": {
            "execution_time": 600.0,
            "success_rate": 1.0,
            "resource_usage": {
                "memory": 2850,
                "cpu": 190,
                "disk": 350,
                "network": 550
            }
        }
    })
    
    # Second execution record with different agent and some failures
    history.append({
        "execution_id": str(uuid.uuid4()),
        "workflow_id": "test_workflow",
        "version_id": "v1",
        "start_time": (now - timedelta(days=1)).isoformat(),
        "end_time": (now - timedelta(days=1) + timedelta(minutes=12)).isoformat(),
        "status": "partial_success",
        "step_results": {
            "fetch_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 62.1,
                    "agent_type": "web_surfer",
                    "agent_id": "agent1",
                    "resource_usage": {
                        "memory": 125,
                        "cpu": 32,
                        "network": 520
                    }
                }
            },
            "process_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 210.5,
                    "agent_type": "alt_processor",  # Different agent type
                    "agent_id": "agent5",
                    "resource_usage": {
                        "memory": 1800,
                        "cpu": 70,
                        "disk": 120
                    }
                }
            },
            "generate_report": {
                "status": "failed",
                "error": "Failed to generate report",
                "metrics": {
                    "execution_time": 45.2,
                    "agent_type": "report_generator",
                    "agent_id": "agent3",
                    "resource_usage": {
                        "memory": 380,
                        "cpu": 40,
                        "disk": 50
                    }
                }
            },
            "send_notification": {
                "status": "skipped",
                "message": "Skipped due to previous failure",
            }
        },
        "metrics": {
            "execution_time": 720.0,
            "success_rate": 0.5,
            "resource_usage": {
                "memory": 2305,
                "cpu": 142,
                "disk": 170,
                "network": 520
            }
        }
    })
    
    # Third execution record with yet another agent choice
    history.append({
        "execution_id": str(uuid.uuid4()),
        "workflow_id": "test_workflow",
        "version_id": "v1",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=8)).isoformat(),
        "status": "success",
        "step_results": {
            "fetch_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 58.3,
                    "agent_type": "enhanced_web_surfer",  # Different agent type
                    "agent_id": "agent6",
                    "resource_usage": {
                        "memory": 110,
                        "cpu": 25,
                        "network": 480
                    }
                }
            },
            "process_data": {
                "status": "success",
                "metrics": {
                    "execution_time": 160.2,
                    "agent_type": "data_processor",
                    "agent_id": "agent2",
                    "resource_usage": {
                        "memory": 2100,
                        "cpu": 85,
                        "disk": 140
                    }
                }
            },
            "generate_report": {
                "status": "success",
                "metrics": {
                    "execution_time": 115.5,
                    "agent_type": "report_generator",
                    "agent_id": "agent3",
                    "resource_usage": {
                        "memory": 430,
                        "cpu": 55,
                        "disk": 180
                    }
                }
            },
            "send_notification": {
                "status": "success",
                "metrics": {
                    "execution_time": 14.8,
                    "agent_type": "notifier",
                    "agent_id": "agent4",
                    "resource_usage": {
                        "memory": 75,
                        "cpu": 9,
                        "network": 45
                    }
                }
            }
        },
        "metrics": {
            "execution_time": 480.0,
            "success_rate": 1.0,
            "resource_usage": {
                "memory": 2715,
                "cpu": 174,
                "disk": 320,
                "network": 525
            }
        }
    })
    
    return history


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id="task1",
        name="process_data",
        description="Process input data",
        agent_type="data_processor",
        parameters={"batch_size": 10, "timeout": 30},
        status="pending",
        max_retries=2,
        timeout=30,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        output=None,
        error=None,
        retry_count=0
    )


@pytest.fixture
def workflow_steps(sample_task):
    """Create a sample workflow with multiple steps."""
    # Create tasks
    task1 = sample_task
    
    task2 = Task(
        id="task2",
        name="analyze_data",
        description="Analyze processed data",
        agent_type="data_analyzer",
        parameters={"depth": 3, "timeout": 60},
        status="pending",
        max_retries=1,
        timeout=60,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        output=None,
        error=None,
        retry_count=0
    )
    
    task3 = Task(
        id="task3",
        name="generate_report",
        description="Generate report from analysis",
        agent_type="report_generator",
        parameters={"format": "pdf", "timeout": 45},
        status="pending",
        max_retries=1,
        timeout=45,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        output=None,
        error=None,
        retry_count=0
    )
    
    task4 = Task(
        id="task4",
        name="send_notification",
        description="Send notification about completed report",
        agent_type="notifier",
        parameters={"channels": ["email", "slack"], "timeout": 15},
        status="pending",
        max_retries=3,
        timeout=15,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        output=None,
        error=None,
        retry_count=0
    )
    
    # Create workflow steps
    return [
        WorkflowStep(task=task1, dependencies=[], parallel=False),
        WorkflowStep(task=task2, dependencies=["process_data"], parallel=False),
        WorkflowStep(task=task3, dependencies=["analyze_data"], parallel=False),
        WorkflowStep(task=task4, dependencies=["generate_report"], parallel=False)
    ]


@pytest.fixture
def execution_history():
    """Create sample execution history for optimization tests."""
    return [
        {
            "execution_id": "exec1",
            "workflow_id": "workflow1",
            "version_id": "v1",
            "status": "success",
            "start_time": "2023-01-01T10:00:00",
            "end_time": "2023-01-01T10:15:00",
            "metrics": {
                "execution_time": 900,
                "success_rate": 1.0
            },
            "step_results": {
                "process_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "data_processor",
                        "execution_time": 300,
                        "resource_usage": {
                            "memory": 500,
                            "cpu": 40
                        }
                    }
                },
                "analyze_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "data_analyzer",
                        "execution_time": 350,
                        "resource_usage": {
                            "memory": 800,
                            "cpu": 70
                        }
                    }
                },
                "generate_report": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "report_generator",
                        "execution_time": 200,
                        "resource_usage": {
                            "memory": 300,
                            "cpu": 30
                        }
                    }
                },
                "send_notification": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "notifier",
                        "execution_time": 50,
                        "resource_usage": {
                            "memory": 100,
                            "cpu": 10
                        }
                    }
                }
            }
        },
        {
            "execution_id": "exec2",
            "workflow_id": "workflow1",
            "version_id": "v1",
            "status": "success",
            "start_time": "2023-01-02T10:00:00",
            "end_time": "2023-01-02T10:14:00",
            "metrics": {
                "execution_time": 840,
                "success_rate": 1.0
            },
            "step_results": {
                "process_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "data_processor",
                        "execution_time": 290,
                        "resource_usage": {
                            "memory": 520,
                            "cpu": 45
                        }
                    }
                },
                "analyze_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "improved_analyzer",
                        "execution_time": 320,
                        "resource_usage": {
                            "memory": 750,
                            "cpu": 65
                        }
                    }
                },
                "generate_report": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "report_generator",
                        "execution_time": 180,
                        "resource_usage": {
                            "memory": 320,
                            "cpu": 35
                        }
                    }
                },
                "send_notification": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "notifier",
                        "execution_time": 50,
                        "resource_usage": {
                            "memory": 100,
                            "cpu": 10
                        }
                    }
                }
            }
        },
        {
            "execution_id": "exec3",
            "workflow_id": "workflow1",
            "version_id": "v1",
            "status": "success",
            "start_time": "2023-01-03T10:00:00",
            "end_time": "2023-01-03T10:13:30",
            "metrics": {
                "execution_time": 810,
                "success_rate": 1.0
            },
            "step_results": {
                "process_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "data_processor",
                        "execution_time": 280,
                        "resource_usage": {
                            "memory": 510,
                            "cpu": 42
                        }
                    }
                },
                "analyze_data": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "improved_analyzer",
                        "execution_time": 300,
                        "resource_usage": {
                            "memory": 730,
                            "cpu": 60
                        }
                    }
                },
                "generate_report": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "report_generator",
                        "execution_time": 190,
                        "resource_usage": {
                            "memory": 310,
                            "cpu": 32
                        }
                    }
                },
                "send_notification": {
                    "status": "success",
                    "metrics": {
                        "agent_type": "notifier",
                        "execution_time": 40,
                        "resource_usage": {
                            "memory": 90,
                            "cpu": 8
                        }
                    }
                }
            }
        }
    ]


@pytest.mark.asyncio
async def test_workflow_optimizer_initialization():
    """Test initialization of the workflow optimizer."""
    optimizer = WorkflowOptimizer()
    assert len(optimizer.strategies) == 3
    assert any(isinstance(strategy, ParallelizationOptimizer) for strategy in optimizer.strategies)
    assert any(isinstance(strategy, AgentSelectionOptimizer) for strategy in optimizer.strategies)
    assert any(isinstance(strategy, ResourceOptimizer) for strategy in optimizer.strategies)


@pytest.mark.asyncio
async def test_parallelization_optimizer(workflow_steps, execution_history):
    """Test the parallelization optimization strategy."""
    optimizer = ParallelizationOptimizer()
    
    # Execute optimization
    optimized_workflow, results = await optimizer.optimize(workflow_steps, execution_history)
    
    # Verify that steps were correctly analyzed for parallelization
    assert "parallelizable_steps" in results
    assert "total_steps" in results
    assert "parallelization_ratio" in results
    
    # Check for meaningful changes
    changes = results.get("changes", [])
    
    # Count parallel steps before and after
    original_parallel_count = sum(1 for step in workflow_steps if step.parallel)
    optimized_parallel_count = sum(1 for step in optimized_workflow if step.parallel)
    
    # If changes were made, verify the increase in parallel steps
    if changes:
        assert optimized_parallel_count > original_parallel_count
        assert results["parallelizable_steps"] > 0


@pytest.mark.asyncio
async def test_agent_selection_optimizer(workflow_steps, execution_history):
    """Test the agent selection optimization strategy."""
    optimizer = AgentSelectionOptimizer()
    
    # Execute optimization
    optimized_workflow, results = await optimizer.optimize(workflow_steps, execution_history)
    
    # Verify that agents were analyzed
    assert "agents_analyzed" in results
    
    # Check for changes in agent assignments
    changes = results.get("changes", [])
    
    if changes:
        # Verify that some tasks got new agent assignments
        for change in changes:
            assert change["type"] == "agent_selection"
            assert change["before"] != change["after"]
            
            # Find the corresponding step in the optimized workflow
            step = next((s for s in optimized_workflow if s.task.name == change["step"]), None)
            assert step is not None
            
            # Verify the agent type was actually changed
            assert step.task.agent_type == change["after"]
            
            # Specifically check if the 'analyze_data' step was optimized to use 'improved_analyzer'
            # based on our execution history
            if change["step"] == "analyze_data":
                assert change["after"] == "improved_analyzer"


@pytest.mark.asyncio
async def test_resource_optimizer(workflow_steps, execution_history):
    """Test the resource optimization strategy."""
    optimizer = ResourceOptimizer()
    
    # Execute optimization
    optimized_workflow, results = await optimizer.optimize(workflow_steps, execution_history)
    
    # Verify that resource usage was analyzed
    assert "resource_types_analyzed" in results
    
    # Check for resource optimization changes
    changes = results.get("changes", [])
    
    if changes:
        for change in changes:
            assert change["type"] == "resource_optimization"
            assert "parameter" in change
            assert "before" in change
            assert "after" in change
            assert "reason" in change
            
            # Find the corresponding step in the optimized workflow
            step = next((s for s in optimized_workflow if s.task.name == change["step"]), None)
            assert step is not None
            
            # Verify the parameter was actually changed
            param = change["parameter"]
            assert param in step.task.parameters
            assert step.task.parameters[param] == change["after"]


@pytest.mark.asyncio
async def test_complete_workflow_optimization(workflow_steps, execution_history):
    """Test the complete workflow optimization process."""
    optimizer = WorkflowOptimizer()
    
    # Execute optimization
    optimized_workflow, results = await optimizer.optimize_workflow(
        workflow_id="workflow1",
        workflow=workflow_steps,
        execution_history=execution_history
    )
    
    # Verify optimization summary structure
    assert "workflow_id" in results
    assert "timestamp" in results
    assert "strategies_applied" in results
    assert "total_changes" in results
    assert "steps_modified" in results
    assert "total_steps" in results
    assert "optimizations" in results
    
    # Verify that steps were modified
    if results["total_changes"] > 0:
        assert results["steps_modified"] > 0
        
        # Verify at least one optimization was applied
        assert len(results["optimizations"]) > 0
        
        # Check that the optimized workflow is different from the original
        assert optimized_workflow != workflow_steps


@pytest.mark.asyncio
async def test_optimizer_management():
    """Test adding and removing optimization strategies."""
    optimizer = WorkflowOptimizer()
    original_count = len(optimizer.strategies)
    
    # Create a custom strategy
    from src.agentic_kernel.orchestrator.workflow_optimizer import WorkflowOptimizationStrategy
    
    class CustomStrategy(WorkflowOptimizationStrategy):
        def __init__(self):
            super().__init__("custom_strategy")
            
        async def optimize(self, workflow, execution_history):
            return workflow, {"strategy": self.name, "changes": []}
    
    # Add the strategy
    custom_strategy = CustomStrategy()
    optimizer.add_strategy(custom_strategy)
    assert len(optimizer.strategies) == original_count + 1
    
    # Remove the strategy
    result = optimizer.remove_strategy("custom_strategy")
    assert result is True
    assert len(optimizer.strategies) == original_count
    
    # Try to remove a non-existent strategy
    result = optimizer.remove_strategy("non_existent_strategy")
    assert result is False
    assert len(optimizer.strategies) == original_count 