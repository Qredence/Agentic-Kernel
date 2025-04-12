"""Worker Agent implementation."""

import asyncio
from typing import Any, Dict

from agentic_kernel.communication.coordination import CoordinationManager

from ..utils.base_agent import Agent, FunctionTool


class WorkerAgent(Agent):
    """Worker Agent responsible for executing assigned tasks."""
    
    def __init__(self, coordination_manager: CoordinationManager):
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
        
        self.coordination_manager = coordination_manager
    
    async def execute_task(self, activity_id: str) -> Dict[str, Any]:
        """Execute an assigned task."""
        # Start the activity
        self.coordination_manager.start_activity(activity_id)
        
        # Simulate task execution
        await asyncio.sleep(1)
        
        # Complete the activity
        self.coordination_manager.complete_activity(activity_id)
        
        return {
            "activity_id": activity_id,
            "status": "completed",
            "result": "Task executed successfully",
        }
    
    async def report_progress(self, activity_id: str) -> Dict[str, Any]:
        """Report progress on a task."""
        status = self.coordination_manager.get_activity_status(activity_id)
        return {
            "activity_id": activity_id,
            "status": status["status"] if status else "unknown",
            "progress": "50%",  # Example progress
        } 