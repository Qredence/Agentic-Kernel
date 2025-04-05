import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from pydantic import ValidationError

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.plugins.file_surfer import FileSurferPlugin, FileInfo

# Simple keywords to guess the desired action
LIST_KEYWORDS = ["list", "show files", "ls"]
READ_KEYWORDS = ["read", "get content", "cat"]
SEARCH_KEYWORDS = ["search", "find text", "grep"]

class FileSurferAgent(Agent):
    """An agent that uses the FileSurferPlugin to interact with the local filesystem."""

    def __init__(self, name: str = "FileSurfer", description: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=name,
            description=description or "Lists, reads, and searches files in a restricted local directory.",
            config=config or {}
        )
        # Pass plugin-specific config (e.g., base_path) if provided
        plugin_config = self.config.get('plugin_config', {})
        if 'base_path' in plugin_config:
            plugin_config['base_path'] = Path(plugin_config['base_path'])
        self.plugin = FileSurferPlugin(**plugin_config)

    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a file operation based on the task description.

        Args:
            task_description: The task (e.g., "list *.py files", "read document.txt", "search for 'TODO' in src").
            context: Optional context (currently unused but part of the interface).

        Returns:
            A dictionary with execution status and results.
        """
        task_lower = task_description.lower()
        words = task_lower.split()

        action = None
        if any(keyword in task_lower for keyword in LIST_KEYWORDS):
            action = 'list'
        elif any(keyword in task_lower for keyword in READ_KEYWORDS):
            action = 'read'
        elif any(keyword in task_lower for keyword in SEARCH_KEYWORDS):
            action = 'search'
        else:
            return {
                'status': 'failure',
                'error_message': "Could not determine file action",
                'output': None
            }

        try:
            if action == 'list':
                # Extract pattern and check for recursive flag
                pattern = "*"
                for word in words:
                    if any(c in word for c in '*?[]'):
                        pattern = word
                        break
                recursive = "recursive" in task_lower
                results = self.plugin.list_files(pattern=pattern, recursive=recursive)
                return {
                    'status': 'success',
                    'output': {'files_listed': [r.model_dump(mode='json') for r in results]}
                }

            elif action == 'read':
                # Extract file path - look for the word after "read" or similar keywords
                file_path = None
                for i, word in enumerate(words):
                    if any(keyword in word for keyword in READ_KEYWORDS) and i + 1 < len(words):
                        file_path = task_description.split()[i + 1]  # Use original case
                        break
                
                if not file_path:
                    return {
                        'status': 'failure',
                        'error_message': 'File path not specified',
                        'output': None
                    }
                
                content = self.plugin.read_file(file_path=file_path)
                if isinstance(content, str) and content.startswith("Error reading file:"):
                    return {
                        'status': 'failure',
                        'error_message': content,
                        'output': None
                    }
                return {
                    'status': 'success',
                    'output': {'file_content': content}
                }

            elif action == 'search':
                # Extract search text and pattern
                text_match = re.search(r"'([^']*)'|\"([^\"]*)\"|`([^`]*)`", task_description)
                if not text_match:
                    return {
                        'status': 'failure',
                        'error_message': 'Search text not specified',
                        'output': None
                    }
                search_text = next(g for g in text_match.groups() if g is not None)
                
                # Extract file pattern after "in" if present
                pattern_match = re.search(r'in\s+(\S+)', task_description.lower())
                file_pattern = pattern_match.group(1) if pattern_match else "*"
                
                results = self.plugin.search_files(text=search_text, file_pattern=file_pattern)
                return {
                    'status': 'success',
                    'output': {'files_found': [r.model_dump(mode='json') for r in results]}
                }

        except Exception as e:
            error_msg = f"An unexpected error occurred during {action}: {str(e)}"
            return {
                'status': 'failure',
                'error_message': error_msg,
                'output': None
            }

        # This should never be reached with current logic
        return {
            'status': 'failure',
            'error_message': f"Action '{action}' is recognized but not implemented yet.",
            'output': None
        }