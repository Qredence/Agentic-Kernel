"""FileSurferAgent implementation for file system operations.

This module provides an agent specialized in file system operations using the
FileSurferPlugin. It supports listing files, reading file contents, and searching
through files with pattern matching.

Key features:
1. File listing with pattern matching and recursive options
2. File content reading with error handling
3. Text search across multiple files
4. Path validation and security checks
5. Natural language command parsing

Example:
    ```python
    # Initialize the file surfer agent
    config = AgentConfig(
        extra_config={
            'plugin_config': {
                'base_path': '/path/to/workspace'
            }
        }
    )
    agent = FileSurferAgent(config)
    
    # List files in a directory
    task = Task(
        description="List all Python files recursively",
        parameters={"pattern": "*.py", "recursive": True}
    )
    result = await agent.execute(task)
    for file in result['output']['files_listed']:
        print(file['path'])
    ```
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Literal
from enum import Enum, auto

from pydantic import ValidationError

from .base import BaseAgent, TaskCapability
from ..plugins.file_surfer import FileSurferPlugin, FileInfo
from ..config_types import AgentConfig
from ..types import Task, TaskStatus
from ..exceptions import TaskExecutionError

import logging

logger = logging.getLogger(__name__)


class FileAction(Enum):
    """Supported file system operations.

    This enum defines the types of operations that the file surfer agent
    can perform on the file system.
    """

    LIST = auto()
    READ = auto()
    SEARCH = auto()


# Action detection keywords
LIST_KEYWORDS = frozenset(["list", "show files", "ls", "dir"])
READ_KEYWORDS = frozenset(["read", "get content", "cat", "view"])
SEARCH_KEYWORDS = frozenset(["search", "find text", "grep", "find"])


class FileSurferResult:
    """Result of a file system operation.

    This class provides a structured way to return results from file operations,
    including the operation status and any relevant data or errors.

    Attributes:
        status (TaskStatus): The status of the operation
        output (Optional[Dict[str, Any]]): Operation results if successful
        error (Optional[str]): Error message if operation failed
    """

    def __init__(
        self,
        status: TaskStatus,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.status = status
        self.output = output
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary format.

        Returns:
            Dictionary containing the operation status and results
        """
        return {"status": self.status, "output": self.output, "error": self.error}


class FileSurferAgent(BaseAgent):
    """Agent for performing file system operations.

    This agent specializes in file system operations using the FileSurferPlugin.
    It can list files, read file contents, and search through files based on
    natural language commands.

    The agent supports pattern matching for file operations and includes
    security measures to prevent unauthorized access outside the base path.

    Attributes:
        plugin (FileSurferPlugin): Plugin for file system operations

    Example:
        ```python
        agent = FileSurferAgent(
            config=AgentConfig(
                extra_config={'plugin_config': {'base_path': '/workspace'}}
            )
        )

        # Read a file
        task = Task(
            description="Read the contents of config.json",
            parameters={"file_path": "config.json"}
        )
        result = await agent.execute(task)
        if result['status'] == TaskStatus.completed:
            print(result['output']['file_content'])
        ```
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the FileSurferAgent.

        Args:
            config: Configuration parameters for the agent, including
                   plugin-specific settings like base_path

        Example:
            ```python
            config = AgentConfig(
                extra_config={
                    'plugin_config': {
                        'base_path': Path('/workspace'),
                        'max_file_size': 1024 * 1024  # 1MB
                    }
                }
            )
            agent = FileSurferAgent(config)
            ```
        """
        super().__init__(config=config)

        # Configure plugin with provided settings
        plugin_config = self.config.extra_config.get("plugin_config", {})
        if "base_path" in plugin_config:
            plugin_config["base_path"] = Path(plugin_config["base_path"])

        # Initialize file system plugin
        self.plugin = FileSurferPlugin(**plugin_config)
        logger.info(
            f"Initialized FileSurferAgent with base path: {plugin_config.get('base_path', 'default')}"
        )

    def _detect_action(self, description: str) -> Optional[FileAction]:
        """Detect the intended file operation from the task description.

        This method analyzes the task description to determine which file
        operation the user wants to perform.

        Args:
            description: Natural language description of the task

        Returns:
            The detected FileAction, or None if no action could be determined

        Example:
            ```python
            action = agent._detect_action("list all python files")
            if action == FileAction.LIST:
                # Handle list operation
            ```
        """
        description_lower = description.lower()

        if any(keyword in description_lower for keyword in LIST_KEYWORDS):
            return FileAction.LIST
        elif any(keyword in description_lower for keyword in READ_KEYWORDS):
            return FileAction.READ
        elif any(keyword in description_lower for keyword in SEARCH_KEYWORDS):
            return FileAction.SEARCH

        return None

    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a file system operation based on the task description.

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
                description="Search for 'TODO' in all Python files",
                parameters={
                    "text": "TODO",
                    "file_pattern": "*.py"
                }
            )
            result = await agent.execute(task)
            if result['status'] == TaskStatus.completed:
                for match in result['output']['files_found']:
                    print(f"Found in {match['path']}")
            ```
        """
        try:
            # Detect intended action
            action = self._detect_action(task.description)
            if not action:
                return FileSurferResult(
                    status=TaskStatus.failed, error="Could not determine file action"
                ).to_dict()

            # Execute appropriate operation
            if action == FileAction.LIST:
                return await self._handle_list(task)
            elif action == FileAction.READ:
                return await self._handle_read(task)
            elif action == FileAction.SEARCH:
                return await self._handle_search(task)

        except Exception as e:
            logger.error(f"File operation failed: {str(e)}", exc_info=True)
            return FileSurferResult(
                status=TaskStatus.failed,
                error=f"An unexpected error occurred: {str(e)}",
            ).to_dict()

    async def _handle_list(self, task: Task) -> Dict[str, Any]:
        """Handle file listing operations.

        Args:
            task: Task containing listing parameters

        Returns:
            Operation result with list of matching files

        Example:
            ```python
            result = await agent._handle_list(Task(
                description="list python files recursively",
                parameters={"pattern": "*.py"}
            ))
            ```
        """
        words = task.description.lower().split()

        # Extract pattern and recursive flag
        pattern = next((word for word in words if any(c in word for c in "*?[]")), "*")
        recursive = "recursive" in task.description.lower()

        try:
            results = self.plugin.list_files(pattern=pattern, recursive=recursive)
            return FileSurferResult(
                status=TaskStatus.completed,
                output={"files_listed": [r.model_dump(mode="json") for r in results]},
            ).to_dict()
        except Exception as e:
            return FileSurferResult(
                status=TaskStatus.failed, error=f"Failed to list files: {str(e)}"
            ).to_dict()

    async def _handle_read(self, task: Task) -> Dict[str, Any]:
        """Handle file reading operations.

        Args:
            task: Task containing the file path to read

        Returns:
            Operation result with file contents

        Example:
            ```python
            result = await agent._handle_read(Task(
                description="read config.json",
                parameters={"file_path": "config.json"}
            ))
            ```
        """
        # Extract file path from description or parameters
        file_path = task.parameters.get("file_path")
        if not file_path:
            words = task.description.split()
            for i, word in enumerate(words):
                if any(keyword in word.lower() for keyword in READ_KEYWORDS):
                    if i + 1 < len(words):
                        file_path = words[i + 1]
                        break

        if not file_path:
            return FileSurferResult(
                status=TaskStatus.failed, error="File path not specified"
            ).to_dict()

        try:
            content = self.plugin.read_file(file_path=file_path)
            if isinstance(content, str) and content.startswith("Error reading file:"):
                return FileSurferResult(
                    status=TaskStatus.failed, error=content
                ).to_dict()

            return FileSurferResult(
                status=TaskStatus.completed, output={"file_content": content}
            ).to_dict()
        except Exception as e:
            return FileSurferResult(
                status=TaskStatus.failed, error=f"Failed to read file: {str(e)}"
            ).to_dict()

    async def _handle_search(self, task: Task) -> Dict[str, Any]:
        """Handle file search operations.

        Args:
            task: Task containing search text and optional file pattern

        Returns:
            Operation result with matching files

        Example:
            ```python
            result = await agent._handle_search(Task(
                description="search for 'TODO' in *.py files",
                parameters={"text": "TODO", "pattern": "*.py"}
            ))
            ```
        """
        # Extract search text
        text_match = re.search(r"'([^']*)'|\"([^\"]*)\"|`([^`]*)`", task.description)
        if not text_match:
            return FileSurferResult(
                status=TaskStatus.failed, error="Search text not specified"
            ).to_dict()

        search_text = next(g for g in text_match.groups() if g is not None)

        # Extract file pattern
        pattern_match = re.search(r"in\s+(\S+)", task.description.lower())
        file_pattern = pattern_match.group(1) if pattern_match else "*"

        try:
            results = self.plugin.search_files(
                text=search_text, file_pattern=file_pattern
            )
            return FileSurferResult(
                status=TaskStatus.completed,
                output={"files_found": [r.model_dump(mode="json") for r in results]},
            ).to_dict()
        except Exception as e:
            return FileSurferResult(
                status=TaskStatus.failed, error=f"Failed to search files: {str(e)}"
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
            "list_files": {
                "description": "List files matching a pattern",
                "parameters": ["pattern"],
                "optional_parameters": ["recursive"],
                "examples": [
                    {
                        "description": "List all Python files recursively",
                        "pattern": "*.py",
                        "recursive": True,
                    }
                ],
            },
            "read_file": {
                "description": "Read the contents of a file",
                "parameters": ["file_path"],
                "optional_parameters": [],
                "examples": [
                    {"description": "Read config.json", "file_path": "config.json"}
                ],
            },
            "search_files": {
                "description": "Search for text in files",
                "parameters": ["text"],
                "optional_parameters": ["file_pattern"],
                "examples": [
                    {
                        "description": "Search for 'TODO' in Python files",
                        "text": "TODO",
                        "file_pattern": "*.py",
                    }
                ],
            },
        }
