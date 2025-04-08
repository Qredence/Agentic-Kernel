"""WebSurferAgent implementation for web search and content retrieval.

This module provides an agent specialized in web operations such as searching
the internet and retrieving/summarizing web content. It handles URL validation,
content extraction, and search result processing with proper error handling.

Key features:
1. Web search with structured results
2. Webpage content summarization
3. URL validation and normalization
4. Error handling for network issues
5. Support for various content types
6. Rate limiting and retry logic

Example:
    ```python
    # Initialize the web surfer agent
    config = AgentConfig(
        extra_config={
            'plugin_config': {
                'search_api_key': 'your-api-key',
                'max_results': 5
            }
        }
    )
    agent = WebSurferAgent(config)
    
    # Perform a web search
    task = Task(
        description="Find recent articles about Python 3.12",
        parameters={"max_results": 3}
    )
    result = await agent.execute(task)
    
    # Print search results
    if result['status'] == 'success':
        for item in result['output']['search_results']:
            print(f"Title: {item['title']}")
            print(f"URL: {item['url']}")
            print(f"Snippet: {item['snippet']}\n")
    ```
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

from pydantic import HttpUrl, ValidationError

from agentic_kernel.config_types import AgentConfig
from agentic_kernel.plugins.web_surfer import WebSearchResult, WebSurferPlugin
from agentic_kernel.types import Task, TaskStatus

from ..plugins.base import BasePlugin
from .base import BaseAgent, TaskCapability

logger = logging.getLogger(__name__)

# URL validation pattern
URL_PATTERN = re.compile(r"https?://[^\s]+")


class WebAction(Enum):
    """Supported web operations.

    This enum defines the types of operations that the web surfer agent
    can perform when interacting with web content.
    """

    SEARCH = auto()  # Perform web search
    SUMMARIZE = auto()  # Summarize webpage content


@dataclass
class WebResult:
    """Result of a web operation.

    This class provides a structured way to return results from web
    operations, including search results and webpage summaries.

    Attributes:
        status (TaskStatus): The status of the operation
        output (Optional[Dict[str, Any]]): Operation results if successful
        error (Optional[str]): Error message if operation failed
    """

    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary format.

        Returns:
            Dictionary containing the operation status and results
        """
        return {"status": self.status, "output": self.output, "error": self.error}


class WebSurferAgent(BaseAgent):
    """Agent for performing web searches and content retrieval.

    This agent specializes in web operations using the WebSurferPlugin.
    It can search the web, summarize webpage content, and handle various
    web-related tasks with proper error handling and rate limiting.

    The agent supports URL validation and content type detection to ensure
    proper handling of different web resources.

    Attributes:
        plugin (WebSurferPlugin): Plugin for web operations

    Example:
        ```python
        agent = WebSurferAgent(
            config=AgentConfig(
                extra_config={
                    'plugin_config': {
                        'search_api_key': 'your-api-key',
                        'max_results': 5,
                        'timeout': 30
                    }
                }
            )
        )

        # Summarize a webpage
        task = Task(
            description="Summarize the content at https://example.com",
            parameters={"url": "https://example.com"}
        )
        result = await agent.execute(task)
        if result['status'] == TaskStatus.completed:
            print(result['output']['summary'])
        ```
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the WebSurferAgent.

        Args:
            config: Configuration parameters for the agent, including
                   plugin-specific settings like API keys and timeouts

        Example:
            ```python
            config = AgentConfig(
                extra_config={
                    'plugin_config': {
                        'search_api_key': 'your-api-key',
                        'max_results': 5,
                        'timeout': 30,
                        'retry_attempts': 3
                    }
                }
            )
            agent = WebSurferAgent(config)
            ```
        """
        super().__init__(config=config)

        # Configure plugin with provided settings
        plugin_config = self.config.extra_config.get("plugin_config", {})
        self.plugin = WebSurferPlugin(**plugin_config)
        logger.info(
            f"Initialized WebSurferAgent with config: "
            f"max_results={plugin_config.get('max_results', 'default')}"
        )

    def _detect_action(self, description: str, context: Dict[str, Any]) -> WebAction:
        """Detect the intended web operation from the task description.

        This method analyzes the task description and context to determine
        which web operation to perform.

        Args:
            description: Natural language description of the task
            context: Additional task parameters and context

        Returns:
            The detected WebAction

        Example:
            ```python
            action = agent._detect_action(
                "summarize https://example.com",
                {"url": "https://example.com"}
            )
            if action == WebAction.SUMMARIZE:
                # Handle webpage summarization
            ```
        """
        # Check for URL in context or description
        url_in_context = bool(context and "url" in context)
        url_in_description = bool(URL_PATTERN.search(description))

        # If URL is present, likely a summarization task
        if url_in_context or url_in_description:
            return WebAction.SUMMARIZE
        # Otherwise, assume it's a search task
        return WebAction.SEARCH

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a web operation based on the task description.

        This method parses the task description to determine the desired
        operation and executes it with appropriate parameters.

        Args:
            task: Task containing the operation description and parameters

        Returns:
            Dictionary containing:
            - status: TaskStatus indicating success or failure
            - output: Operation results if successful
            - error: Error message if operation failed

        Raises:
            TaskExecutionError: If task execution fails unexpectedly

        Example:
            ```python
            task = Task(
                description="Search for Python tutorials",
                parameters={"max_results": 5}
            )
            result = await agent.execute(task)
            if result['status'] == TaskStatus.completed:
                for item in result['output']['search_results']:
                    print(f"{item['title']}: {item['url']}")
            ```
        """
        try:
            context = task.parameters or {}

            # Detect action type
            action = self._detect_action(task.description, context)

            # Execute appropriate operation
            if action == WebAction.SUMMARIZE:
                return await self._handle_summarize(task.description, context)
            else:
                return await self._handle_search(task.description, context)

        except Exception as e:
            logger.error(f"Web operation failed: {str(e)}", exc_info=True)
            return WebResult(
                status=TaskStatus.failed,
                error=f"An unexpected error occurred: {str(e)}",
            ).to_dict()

    async def _handle_search(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle web search operation.

        Args:
            query: The search query
            context: Additional parameters like max_results

        Returns:
            Operation result with search results

        Example:
            ```python
            result = await agent._handle_search(
                "Python tutorials",
                {"max_results": 5}
            )
            if result['status'] == TaskStatus.completed:
                for item in result['output']['search_results']:
                    print(item['title'])
            ```
        """
        try:
            # Use asyncio.to_thread for sync plugin method
            results = await asyncio.to_thread(
                self.plugin.web_search, query=query, **context
            )

            # Convert results to dictionaries
            output_results = [result.model_dump() for result in results]

            return WebResult(
                status=TaskStatus.completed, output={"search_results": output_results}
            ).to_dict()

        except Exception as e:
            logger.error(f"Search operation failed: {str(e)}", exc_info=True)
            return WebResult(
                status=TaskStatus.failed,
                error=f"Failed to perform web search: {str(e)}",
            ).to_dict()

    async def _handle_summarize(
        self, description: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle webpage summarization.

        Args:
            description: Task description that may contain URL
            context: Additional parameters including possible URL

        Returns:
            Operation result with webpage summary

        Example:
            ```python
            result = await agent._handle_summarize(
                "Summarize https://example.com",
                {"url": "https://example.com"}
            )
            if result['status'] == TaskStatus.completed:
                print(result['output']['summary'])
            ```
        """
        try:
            # Try to get URL from context first
            url_str = context.get("url")
            if not url_str:
                # Try to extract URL from description
                match = URL_PATTERN.search(description)
                if match:
                    url_str = match.group(0)
                else:
                    return WebResult(
                        status=TaskStatus.failed, error="No valid URL found in task"
                    ).to_dict()

            try:
                url = HttpUrl(str(url_str))
            except ValidationError:
                return WebResult(
                    status=TaskStatus.failed, error=f"Invalid URL format: {url_str}"
                ).to_dict()

            # Use asyncio.to_thread for sync plugin method
            summary = await asyncio.to_thread(self.plugin.summarize_webpage, url=url)

            # Check for error string from plugin
            if isinstance(summary, str) and summary.startswith("Error"):
                return WebResult(status=TaskStatus.failed, error=summary).to_dict()

            return WebResult(
                status=TaskStatus.completed, output={"summary": summary}
            ).to_dict()

        except Exception as e:
            logger.error(
                f"Summarization failed for URL {url_str}: {str(e)}", exc_info=True
            )
            return WebResult(
                status=TaskStatus.failed, error=f"Failed to summarize webpage: {str(e)}"
            ).to_dict()

    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dictionary mapping task types to their capabilities

        Example:
            ```python
            capabilities = agent._get_supported_tasks()
            for task_type, details in capabilities.items():
                print(f"{task_type}: {details['description']}")
            ```
        """
        return {
            "web_search": {
                "description": "Search the web for information",
                "parameters": ["query"],
                "optional_parameters": ["max_results", "language"],
                "examples": [
                    {
                        "description": "Find Python tutorials",
                        "query": "Python beginner tutorials",
                        "max_results": 5,
                    }
                ],
            },
            "summarize_webpage": {
                "description": "Generate a summary of a webpage",
                "parameters": ["url"],
                "optional_parameters": ["max_length"],
                "examples": [
                    {
                        "description": "Summarize article at https://example.com",
                        "url": "https://example.com",
                        "max_length": 500,
                    }
                ],
            },
        }
