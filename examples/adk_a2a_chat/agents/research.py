"""Research Agent for the ADK A2A Chat System."""

import asyncio
import logging
from typing import Any

from google.adk.tools import FunctionTool

from ..utils.adk_a2a_utils import ADKA2AAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResearchAgent(ADKA2AAgent):
    """Research Agent that retrieves and summarizes information."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
    ):
        """Initialize the ResearchAgent.

        Args:
            host: The host for the A2A server
            port: The port for the A2A server
        """
        super().__init__(
            name="research",
            description="Research Agent that retrieves and summarizes information",
            model="gemini-2.0-flash-exp",
            host=host,
            port=port,
        )

        # Add tools for research
        self.add_tool(
            FunctionTool(
                name="search_information",
                description="Search for information on a given query",
                function=self.search_information,
            ),
        )

        self.add_tool(
            FunctionTool(
                name="summarize_information",
                description="Summarize information from multiple sources",
                function=self.summarize_information,
            ),
        )

        # Register A2A methods
        self.register_a2a_method("tasks.send", self.handle_tasks_send)
        self.register_a2a_method("tasks.get", self.handle_tasks_get)

    async def search_information(self, query: str) -> dict[str, Any]:
        """Search for information on a given query.

        Args:
            query: The search query

        Returns:
            Search results
        """
        logger.info(f"Searching for information on: {query}")
        
        # This is a simplified implementation
        # In a real system, this would use external APIs or databases to search for information
        
        # Simulate a search delay
        await asyncio.sleep(1)
        
        # Return mock search results
        return {
            "query": query,
            "results": [
                {
                    "title": f"Information about {query}",
                    "snippet": f"This is some information about {query}...",
                    "source": "example.com",
                },
                {
                    "title": f"{query} - Additional Details",
                    "snippet": f"More details about {query}...",
                    "source": "example.org",
                },
            ],
        }

    async def summarize_information(
        self,
        query: str,
        search_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Summarize information from multiple sources.

        Args:
            query: The original query
            search_results: The search results to summarize

        Returns:
            A summary of the information
        """
        logger.info(f"Summarizing information for query: {query}")
        
        # This is a simplified implementation
        # In a real system, this would use the ADK agent to generate a summary
        
        # Extract snippets from search results
        snippets = [result["snippet"] for result in search_results]
        
        # Simulate summarization delay
        await asyncio.sleep(1)
        
        # Generate a mock summary
        summary = f"Based on the search results, {query} refers to... [summary of information]"
        
        return {
            "query": query,
            "summary": summary,
            "sources": [result["source"] for result in search_results],
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
        if "research" in description.lower() or "information" in description.lower():
            query = task_input.get("query", "")
            
            # Search for information
            search_results = await self.search_information(query)
            
            # Summarize the information
            summary = await self.summarize_information(
                query=query,
                search_results=search_results["results"],
            )
            
            return {
                "status": "completed",
                "result": summary["summary"],
                "sources": summary["sources"],
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
            "result": "Research results for the requested task",
        }