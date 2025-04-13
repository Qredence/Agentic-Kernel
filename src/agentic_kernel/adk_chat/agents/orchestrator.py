"""Orchestrator Agent for the ADK A2A Chat System."""

import logging
from typing import Any

from agentic_kernel.communication.coordination import CoordinationManager
from agentic_kernel.communication.trust import TrustManager
from google.adk.tools import FunctionTool

from ..utils.adk_a2a_utils import ADKA2AAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestratorAgent(ADKA2AAgent):
    """Orchestrator Agent that coordinates the conversation and delegates tasks."""

    def __init__(
        self,
        coordination_manager: CoordinationManager,
        trust_manager: TrustManager,
        host: str = "localhost",
        port: int = 8000,
    ):
        """Initialize the OrchestratorAgent.

        Args:
            coordination_manager: The coordination manager
            trust_manager: The trust manager
            host: The host for the A2A server
            port: The port for the A2A server
        """
        super().__init__(
            name="orchestrator",
            description="Orchestrator Agent that coordinates the conversation and delegates tasks",
            model="gemini-2.0-flash-exp",
            host=host,
            port=port,
        )

        self.coordination_manager = coordination_manager
        self.trust_manager = trust_manager

        # Add tools for orchestration
        self.add_tool(
            FunctionTool(
                name="process_user_message",
                description="Process a message from the user and coordinate a response",
                function=self.process_user_message,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="delegate_task",
                description="Delegate a task to a specialized agent",
                function=self.delegate_task,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="combine_responses",
                description="Combine responses from multiple agents into a coherent response",
                function=self.combine_responses,
            ),
        )

        # Register A2A methods
        self.register_a2a_method("tasks.send", self.handle_tasks_send)
        self.register_a2a_method("tasks.get", self.get_task_info)

    async def process_user_message(self, message: str) -> dict[str, Any]:
        """Process a message from the user and coordinate a response.

        Args:
            message: The user's message

        Returns:
            A response to the user
        """
        logger.info(f"Processing user message: {message}")

        # Analyze the message to determine which agents to involve
        task_type = await self._determine_task_type(message)

        # Create a coordination activity for this message
        activity_id = self.coordination_manager.create_activity(
            name=f"User message: {message[:30]}...",
            description=message,
            agent_id="orchestrator",
            priority="high",
        )

        # Delegate tasks to appropriate agents based on the task type
        agent_responses = {}

        if "research" in task_type:
            research_response = await self.delegate_task(
                agent_name="research",
                task_description="Research information",
                params={"query": message},
            )
            agent_responses["research"] = research_response

        if "creative" in task_type:
            creative_response = await self.delegate_task(
                agent_name="creative",
                task_description="Generate creative content",
                params={"prompt": message},
            )
            agent_responses["creative"] = creative_response

        if "reasoning" in task_type:
            reasoning_response = await self.delegate_task(
                agent_name="reasoning",
                task_description="Perform logical reasoning",
                params={"problem": message},
            )
            agent_responses["reasoning"] = reasoning_response

        # Combine the responses
        combined_response = await self.combine_responses(
            responses=agent_responses,
            original_message=message,
        )

        # Update the activity status
        self.coordination_manager.update_activity_status(
            activity_id=activity_id,
            status="completed",
            result={"response": combined_response},
        )

        return {
            "activity_id": activity_id,
            "response": combined_response,
        }

    async def _determine_task_type(self, message: str) -> list[str]:
        """Determine the type of task based on the user's message.

        Args:
            message: The user's message

        Returns:
            A list of task types (research, creative, reasoning)
        """
        # This is a simplified implementation
        # In a real system, this would use the ADK agent to analyze the message

        task_types = []

        # Check for research-related keywords
        research_keywords = [
            "find",
            "search",
            "information",
            "data",
            "what is",
            "who is",
            "when",
            "where",
        ]
        if any(keyword in message.lower() for keyword in research_keywords):
            task_types.append("research")

        # Check for creative-related keywords
        creative_keywords = [
            "create",
            "generate",
            "write",
            "design",
            "story",
            "poem",
            "imagine",
        ]
        if any(keyword in message.lower() for keyword in creative_keywords):
            task_types.append("creative")

        # Check for reasoning-related keywords
        reasoning_keywords = [
            "analyze",
            "solve",
            "reason",
            "logic",
            "why",
            "how",
            "explain",
        ]
        if any(keyword in message.lower() for keyword in reasoning_keywords):
            task_types.append("reasoning")

        # If no specific task type is identified, include all types
        if not task_types:
            task_types = ["research", "creative", "reasoning"]

        return task_types

    async def delegate_task(
        self,
        agent_name: str,
        task_description: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Delegate a task to a specialized agent.

        Args:
            agent_name: The name of the agent to delegate to
            task_description: A description of the task
            params: Input parameters for the task

        Returns:
            The task result
        """
        logger.info(f"Delegating task '{task_description}' to {agent_name}")

        try:
            # Send the task to the agent via A2A
            return await self.send_task(
                recipient_agent=agent_name,
                task_description=task_description,
                params=params,
            )
        except Exception as e:
            logger.error(f"Error delegating task to {agent_name}: {e}")
            return {
                "error": f"Failed to delegate task to {agent_name}: {e}",
                "status": "failed",
            }

    async def combine_responses(
        self,
        responses: dict[str, dict[str, Any]],
        _original_message: str,  # Mark as unused
    ) -> str:
        """Combine responses from multiple agents into a coherent response.

        Args:
            responses: A dictionary of agent responses
            _original_message: The original user message (unused)

        Returns:
            A combined response
        """
        logger.info(f"Combining responses from {len(responses)} agents")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to generate a coherent response

        combined_parts = []

        # Add research information if available
        if "research" in responses and "result" in responses["research"]:
            research_result = responses["research"]["result"]
            combined_parts.append(f"Research findings: {research_result}")

        # Add creative content if available
        if "creative" in responses and "content" in responses["creative"]:
            creative_content = responses["creative"]["content"]
            combined_parts.append(f"Creative response: {creative_content}")

        # Add reasoning if available
        if "reasoning" in responses and "analysis" in responses["reasoning"]:
            reasoning_analysis = responses["reasoning"]["analysis"]
            combined_parts.append(f"Analysis: {reasoning_analysis}")

        # If no valid responses, provide a fallback
        if not combined_parts:
            return "I'm sorry, I wasn't able to process your request properly. Could you please rephrase or provide more details?"

        # Join the parts with line breaks
        return "\n\n".join(combined_parts)

    async def handle_tasks_send(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an A2A tasks.send request.

        Args:
            params: The request parameters

        Returns:
            The response
        """
        logger.info(
            f"Processing task '{params.get('description', '')}' with input: {params.get('input', {})}"
        )
        # Directly return the simulated result
        return {
            "task_id": "task_123",
            "status": "processing",
            "result": f"Processed: {params.get('description', '')}",
        }

    async def get_task_info(self, task_id: str) -> dict[str, Any] | None:
        """Get information about a specific task."""
        logger.info(f"Received task info request for {task_id}")
        # Retrieve task info using CoordinationManager
        return self.coordination_manager.get_task_info(task_id)
