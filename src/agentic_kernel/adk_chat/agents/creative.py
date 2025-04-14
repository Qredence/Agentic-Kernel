"""Creative Agent for the ADK A2A Chat System."""

import asyncio
import logging
from typing import Any

from google.adk.tools import FunctionTool

from ..utils.adk_a2a_utils import ADKA2AAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreativeAgent(ADKA2AAgent):
    """Creative Agent that generates creative content."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8002,
    ):
        """Initialize the CreativeAgent.

        Args:
            host: The host for the A2A server
            port: The port for the A2A server
        """
        super().__init__(
            name="creative",
            description="Creative Agent that generates creative content",
            model="gemini-2.0-flash-exp",
            host=host,
            port=port,
        )

        # Add tools for creative content generation
        self.add_tool(
            FunctionTool(
                name="generate_story",
                description="Generate a creative story based on a prompt",
                function=self.generate_story,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="generate_poem",
                description="Generate a poem based on a prompt",
                function=self.generate_poem,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="generate_creative_response",
                description="Generate a creative response to a prompt",
                function=self.generate_creative_response,
            ),
        )

        # Register A2A methods
        self.register_a2a_method("tasks.send", self.handle_tasks_send)
        self.register_a2a_method("tasks.get", self.handle_tasks_get)

    async def generate_story(
        self, prompt: str, length: str = "medium"
    ) -> dict[str, Any]:
        """Generate a creative story based on a prompt.

        Args:
            prompt: The story prompt
            length: The desired length of the story (short, medium, long)

        Returns:
            The generated story
        """
        logger.info(f"Generating story for prompt: {prompt}, length: {length}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to generate a story

        # Simulate generation delay
        await asyncio.sleep(1)

        # Generate a mock story
        if length == "short":
            story = f"Once upon a time, {prompt}... [short story]"
        elif length == "long":
            story = f"Once upon a time, {prompt}... [long story with multiple paragraphs and character development]"
        else:  # medium
            story = f"Once upon a time, {prompt}... [medium-length story with a beginning, middle, and end]"

        return {
            "prompt": prompt,
            "length": length,
            "story": story,
        }

    async def generate_poem(self, prompt: str, style: str = "free") -> dict[str, Any]:
        """Generate a poem based on a prompt.

        Args:
            prompt: The poem prompt
            style: The style of the poem (free, haiku, sonnet)

        Returns:
            The generated poem
        """
        logger.info(f"Generating poem for prompt: {prompt}, style: {style}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to generate a poem

        # Simulate generation delay
        await asyncio.sleep(1)

        # Generate a mock poem based on style
        if style == "haiku":
            poem = f"{prompt} inspires\nCreative words flow gently\nNature awakens"
        elif style == "sonnet":
            poem = f"A sonnet about {prompt}...\n[14 lines of iambic pentameter]"
        else:  # free
            poem = (
                f"A free verse poem about {prompt}...\n[creative arrangement of lines]"
            )

        return {
            "prompt": prompt,
            "style": style,
            "poem": poem,
        }

    async def generate_creative_response(self, prompt: str) -> dict[str, Any]:
        """Generate a creative response to a prompt.

        Args:
            prompt: The prompt for the creative response

        Returns:
            The creative response
        """
        logger.info(f"Generating creative response for prompt: {prompt}")

        # This is a simplified implementation
        # In a real system, this would use the ADK agent to generate a creative response

        # Determine the type of creative content to generate
        if "story" in prompt.lower():
            result = await self.generate_story(prompt)
            content = result["story"]
            content_type = "story"
        elif "poem" in prompt.lower():
            result = await self.generate_poem(prompt)
            content = result["poem"]
            content_type = "poem"
        else:
            # Generate a generic creative response
            await asyncio.sleep(1)
            content = f"A creative response to '{prompt}'... [imaginative content]"
            content_type = "creative_text"

        return {
            "prompt": prompt,
            "content": content,
            "content_type": content_type,
        }

    async def handle_tasks_send(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an A2A tasks.send request.

        Args:
            params: The request parameters

        Returns:
            The response
        """
        logger.info(f"Received tasks.send request: {params}")

        # Extract task information
        description = params.get("description", "")
        task_input = params.get("input", {})

        # Process based on the task description
        if "creative" in description.lower() or "generate" in description.lower():
            prompt = task_input.get("prompt", "")

            # Generate creative content
            result = await self.generate_creative_response(prompt)

            return {
                "status": "completed",
                "content": result["content"],
                "content_type": result["content_type"],
            }

        # Default response for unknown tasks
        return {
            "status": "failed",
            "error": f"Unknown task type: {description}",
        }

    async def handle_tasks_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle an A2A tasks.get request.

        Args:
            params: The request parameters

        Returns:
            The response
        """
        logger.info(f"Received tasks.get request: {params}")

        # Extract task ID
        task_id = params.get("task_id", "")

        # This is a simplified implementation
        # In a real system, this would retrieve the task status from a database

        return {
            "task_id": task_id,
            "status": "completed",
            "content": "Creative content for the requested task",
            "content_type": "creative_text",
        }
