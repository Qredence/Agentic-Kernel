"""Task Manager Agent implementation."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agentic_kernel.communication.coordination import (
    Activity,
    ActivityPriority,
    ActivityStatus,
    CoordinationManager,
)

from ..utils.base_agent import Agent, FunctionTool

logger = logging.getLogger(__name__)


class TaskManagerAgent(Agent):
    """Task Manager Agent responsible for coordinating and delegating tasks."""
    
    def __init__(self, coordination_manager: CoordinationManager):
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
        
        self.coordination_manager = coordination_manager
    
    async def create_task(
        self,
        task_description: str,
        priority: str,
        deadline: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task and assign it to a worker agent."""
        # Create activity in coordination manager
        activity_id = self.coordination_manager.create_activity(
            name=f"Task: {task_description[:30]}...",
            description=task_description,
            agent_id="worker_agent",  # Assign to worker agent
            estimated_duration=3600,  # 1 hour default
            priority=ActivityPriority[priority.upper()],
        )
        
        # Schedule the activity immediately for simplicity in this example
        scheduled_successfully = self.coordination_manager.schedule_activity(
            activity_id=activity_id, 
            start_time=datetime.utcnow()
        )
        if not scheduled_successfully:
            # Handle scheduling failure (e.g., log warning, return error)
            logger.warning(f"Failed to schedule activity {activity_id}")
            # Depending on requirements, might want to return an error status here

        # Schedule the activity based on deadline if provided (This part might need adjustment)
        # If a deadline exists, we might want schedule_activity to handle it,
        # or update the schedule if already set above.
        # For now, let's comment out the explicit deadline scheduling 
        # as schedule_activity doesn't currently support rescheduling/updates.
        # if deadline:
        #     deadline_dt = datetime.fromisoformat(deadline)
        #     # Note: schedule_activity might need modification to handle updates
        #     # or we need a separate update_schedule method.
        #     self.coordination_manager.schedule_activity(activity_id, deadline_dt)
        
        return {
            "activity_id": activity_id,
            "status": "created",
            "assigned_to": "worker_agent",
        }
    
    async def monitor_tasks(self) -> List[Dict[str, Any]]:
        """Monitor the status of all active tasks."""
        return self.coordination_manager.get_activity_timeline() 