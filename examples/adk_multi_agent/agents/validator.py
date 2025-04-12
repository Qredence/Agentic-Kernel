"""Validator Agent implementation."""

import asyncio
from typing import Any, Dict

from agentic_kernel.communication.coordination import CoordinationManager
from agentic_kernel.communication.trust import TrustManager

from ..utils.base_agent import Agent, FunctionTool


class ValidatorAgent(Agent):
    """Validator Agent responsible for validating task results."""
    
    def __init__(self, coordination_manager: CoordinationManager, trust_manager: TrustManager):
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
        
        self.coordination_manager = coordination_manager
        self.trust_manager = trust_manager
    
    async def validate_task(self, activity_id: str) -> Dict[str, Any]:
        """Validate a completed task."""
        status = self.coordination_manager.get_activity_status(activity_id)
        
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
        """Update trust metrics based on task validation."""
        self.trust_manager.update_trust_based_on_interaction(
            agent_id=agent_id,
            success=success,
            interaction_type=interaction_type,
        )
        
        return {
            "agent_id": agent_id,
            "trust_score": self.trust_manager.calculate_trust_score(agent_id),
            "status": "updated",
        } 