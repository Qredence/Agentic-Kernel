"""Terminal plugin for executing shell commands."""

import asyncio
import os
from typing import Dict, List, Optional, Any
from .base import BasePlugin


class TerminalPlugin(BasePlugin):
    """Plugin for executing terminal commands."""

    def __init__(self):
        super().__init__()
        self.name = "terminal"
        self.description = "Plugin for executing terminal commands"
        self.current_dir = os.getcwd()

    async def execute_command(
        self, command: str, background: bool = False
    ) -> Dict[str, Any]:
        """Execute a shell command.

        Args:
            command: The command to execute
            background: Whether to run in background

        Returns:
            Dict containing command output and status
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.current_dir,
            )

            if background:
                return {"success": True, "background": True, "pid": process.pid}

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "code": process.returncode,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def change_directory(self, path: str) -> Dict[str, Any]:
        """Change the current working directory.

        Args:
            path: New directory path

        Returns:
            Dict indicating success/failure
        """
        try:
            os.chdir(path)
            self.current_dir = os.getcwd()
            return {"success": True, "new_dir": self.current_dir}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_current_directory(self) -> str:
        """Get the current working directory.

        Returns:
            Current directory path
        """
        return self.current_dir
