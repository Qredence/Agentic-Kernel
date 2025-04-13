"""Example multi-agent system using Google ADK framework.

This example demonstrates how to create a multi-agent system using Google's
Agent Development Kit (ADK) framework, integrating with our A2A communication
protocols and coordination mechanisms.

The example implements a simple task management system with three agents:
1. Task Manager Agent - Coordinates and delegates tasks
2. Worker Agent - Executes assigned tasks
3. Validator Agent - Validates task results

Key features demonstrated:
1. ADK agent creation and configuration
2. A2A-style communication between agents
3. Task coordination and delegation
4. Result validation and feedback
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

from agentic_kernel.communication.coordination import (
    Activity,
    ActivityPriority,
    ActivityStatus,
    CoordinationManager,
)
from agentic_kernel.communication.trust import TrustManager


# Temporary placeholder classes until ADK is available
class Agent:
    def __init__(self, name: str, model: str, instruction: str):
        self.name = name
        self.model = model
        self.instruction = instruction
        self.tools = []

    def add_tool(self, tool):
        self.tools.append(tool)

class InMemorySessionService:
    def create_session(self, state: Dict, app_name: str, user_id: str):
        return {"state": state, "app_name": app_name, "user_id": user_id}

class FunctionTool:
    def __init__(self, name: str, description: str, function: callable):
        self.name = name
        self.description = description
        self.function = function


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize managers
coordination_manager = CoordinationManager()
trust_manager = TrustManager()

class TaskManagerAgent(Agent):
    """Task Manager Agent responsible for coordinating and delegating tasks."""
    
    def __init__(self):
        super().__init__(
            name="task_manager",
            model="gemini-2.0-flash-exp",
            instruction="""
            You are a Task Manager Agent responsible for coordinating and delegating tasks.
            Your responsibilities include:
            1. Breaking down complex tasks into subtasks
            2. Assigning tasks to appropriate worker agents
            3. Monitoring task progress
            4. Validating completed tasks
            """,
        )
        
        # Add tools for task management
        self.add_tool(FunctionTool(
            name="create_task",
            description="Create a new task and assign it to a worker agent",
            function=self.create_task,
        ))
        
        self.add_tool(FunctionTool(
            name="monitor_tasks",
            description="Monitor the status of all active tasks",
            function=self.monitor_tasks,
        ))
    
    async def create_task(
        self,
        task_description: str,
        priority: str,
        deadline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task and assign it to a worker agent.
        
        Args:
            task_description: Description of the task
            priority: Priority level (low, medium, high, critical)
            deadline: Optional deadline for the task
            
        Returns:
            Task creation result
        """
        # Create activity in coordination manager
        activity_id = coordination_manager.create_activity(
            name=f"Task: {task_description[:30]}...",
            description=task_description,
            agent_id="worker_agent",  # Assign to worker agent
            estimated_duration=3600,  # 1 hour default
            priority=ActivityPriority[priority.upper()],
        )
        
        # Schedule the activity
        if deadline:
            deadline_dt = datetime.fromisoformat(deadline)
            coordination_manager.schedule_activity(activity_id, deadline_dt)
        
        return {
            "activity_id": activity_id,
            "status": "created",
            "assigned_to": "worker_agent",
        }
    
    async def monitor_tasks(self) -> List[Dict[str, Any]]:
        """Monitor the status of all active tasks.
        
        Returns:
            List of task statuses
        """
        return coordination_manager.get_activity_timeline()

class WorkerAgent(Agent):
    """Worker Agent responsible for executing assigned tasks."""
    
    def __init__(self):
        super().__init__(
            name="worker",
            model="gemini-2.0-flash-exp",
            instruction="""
            You are a Worker Agent responsible for executing assigned tasks.
            Your responsibilities include:
            1. Receiving and understanding task assignments
            2. Executing tasks efficiently
            3. Reporting progress and results
            4. Handling task failures gracefully
            """,
        )
        
        # Add tools for task execution
        self.add_tool(FunctionTool(
            name="execute_task",
            description="Execute an assigned task",
            function=self.execute_task,
        ))
        
        self.add_tool(FunctionTool(
            name="report_progress",
            description="Report progress on a task",
            function=self.report_progress,
        ))
    
    async def execute_task(self, activity_id: str) -> Dict[str, Any]:
        """Execute an assigned task.
        
        Args:
            activity_id: ID of the activity to execute
            
        Returns:
            Task execution result
        """
        # Start the activity
        coordination_manager.start_activity(activity_id)
        
        # Simulate task execution
        await asyncio.sleep(1)
        
        # Complete the activity
        coordination_manager.complete_activity(activity_id)
        
        return {
            "activity_id": activity_id,
            "status": "completed",
            "result": "Task executed successfully",
        }
    
    async def report_progress(self, activity_id: str) -> Dict[str, Any]:
        """Report progress on a task.
        
        Args:
            activity_id: ID of the activity
            
        Returns:
            Progress report
        """
        status = coordination_manager.get_activity_status(activity_id)
        return {
            "activity_id": activity_id,
            "status": status["status"] if status else "unknown",
            "progress": "50%",  # Example progress
        }

class ValidatorAgent(Agent):
    """Validator Agent responsible for validating task results."""
    
    def __init__(self):
        super().__init__(
            name="validator",
            model="gemini-2.0-flash-exp",
            instruction="""
            You are a Validator Agent responsible for validating task results.
            Your responsibilities include:
            1. Reviewing completed tasks
            2. Validating task results
            3. Providing feedback
            4. Updating trust metrics
            """,
        )
        
        # Add tools for validation
        self.add_tool(FunctionTool(
            name="validate_task",
            description="Validate a completed task",
            function=self.validate_task,
        ))
        
        self.add_tool(FunctionTool(
            name="update_trust",
            description="Update trust metrics based on task validation",
            function=self.update_trust,
        ))
    
    async def validate_task(self, activity_id: str) -> Dict[str, Any]:
        """Validate a completed task.
        
        Args:
            activity_id: ID of the activity to validate
            
        Returns:
            Validation result
        """
        status = coordination_manager.get_activity_status(activity_id)
        
        if not status or status["status"] != "completed":
            return {
                "activity_id": activity_id,
                "status": "invalid",
                "reason": "Task not completed",
            }
        
        # Simulate validation
        await asyncio.sleep(0.5)
        
        return {
            "activity_id": activity_id,
            "status": "valid",
            "feedback": "Task completed successfully and meets requirements",
        }
    
    async def update_trust(
        self,
        agent_id: str,
        success: bool,
        interaction_type: str = "task_execution",
    ) -> Dict[str, Any]:
        """Update trust metrics based on task validation.
        
        Args:
            agent_id: ID of the agent
            success: Whether the task was successful
            interaction_type: Type of interaction
            
        Returns:
            Trust update result
        """
        trust_manager.update_trust_based_on_interaction(
            agent_id=agent_id,
            success=success,
            interaction_type=interaction_type,
        )
        
        return {
            "agent_id": agent_id,
            "trust_score": trust_manager.calculate_trust_score(agent_id),
            "status": "updated",
        }

async def main():
    """Main function to run the multi-agent system."""
    # Initialize session service
    session_service = InMemorySessionService()
    
    # Create agents
    task_manager = TaskManagerAgent()
    worker = WorkerAgent()
    validator = ValidatorAgent()
    
    # Create a session
    session = session_service.create_session(
        state={},
        app_name="multi_agent_system",
        user_id="user1",
    )
    
    # Example task
    task_description = "Process and analyze customer feedback data"
    
    # Task Manager creates and assigns task
    task_result = await task_manager.create_task(
        task_description=task_description,
        priority="high",
        deadline=(datetime.utcnow() + timedelta(hours=1)).isoformat(),
    )
    
    # Worker executes task
    execution_result = await worker.execute_task(task_result["activity_id"])
    
    # Validator validates result
    validation_result = await validator.validate_task(task_result["activity_id"])
    
    # Update trust metrics
    trust_update = await validator.update_trust(
        agent_id="worker_agent",
        success=validation_result["status"] == "valid",
    )
    
    logger.info("Task execution completed:")
    logger.info(f"Task creation: {task_result}")
    logger.info(f"Task execution: {execution_result}")
    logger.info(f"Task validation: {validation_result}")
    logger.info(f"Trust update: {trust_update}")

if __name__ == "__main__":
    asyncio.run(main()) 