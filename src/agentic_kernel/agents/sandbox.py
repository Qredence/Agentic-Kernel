"""Docker sandbox for secure agent execution."""

import os
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

import docker
from docker.errors import DockerException

from ..config.agent_team import DockerSandboxConfig

logger = logging.getLogger(__name__)


class DockerSandbox:
    """A Docker-based sandbox for secure agent execution."""

    def __init__(self, config: DockerSandboxConfig):
        """Initialize the Docker sandbox.

        Args:
            config: Docker sandbox configuration
        """
        self.config = config
        self.client = docker.from_env()
        self.container = None
        self.workspace = None

    async def setup(self) -> None:
        """Set up the sandbox environment."""
        try:
            # Create temporary workspace
            self.workspace = Path(tempfile.mkdtemp(prefix="agentic_sandbox_"))
            logger.info(f"Created sandbox workspace at {self.workspace}")

            # Pull the Docker image if needed
            try:
                self.client.images.get(self.config.image)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling Docker image {self.config.image}...")
                self.client.images.pull(self.config.image)

            # Create container with workspace mounted
            self.container = self.client.containers.create(
                image=self.config.image,
                command="tail -f /dev/null",  # Keep container running
                volumes={str(self.workspace): {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                environment=self.config.environment or {},
                network_mode=self.config.network_mode or "none",
                mem_limit=self.config.memory_limit or "512m",
                cpu_period=100000,  # Docker default
                cpu_quota=int(100000 * (self.config.cpu_limit or 1.0)),
                security_opt=["no-new-privileges"],
                cap_drop=["ALL"],
            )

            # Start the container
            self.container.start()
            logger.info(f"Started sandbox container {self.container.short_id}")

        except DockerException as e:
            logger.error(f"Failed to set up Docker sandbox: {e}")
            await self.cleanup()
            raise

    async def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Run a command in the sandbox.

        Args:
            command: Command to run
            timeout: Command timeout in seconds

        Returns:
            Dictionary containing exit code, stdout, and stderr
        """
        if not self.container:
            raise RuntimeError("Sandbox not initialized. Call setup() first.")

        try:
            result = self.container.exec_run(
                command,
                workdir="/workspace",
                demux=True,
                tty=True,
            )

            exit_code = result.exit_code
            stdout = result.output[0].decode() if result.output[0] else ""
            stderr = result.output[1].decode() if result.output[1] else ""

            return {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}

        except DockerException as e:
            logger.error(f"Failed to run command in sandbox: {e}")
            return {"exit_code": -1, "stdout": "", "stderr": str(e)}

    async def cleanup(self) -> None:
        """Clean up sandbox resources."""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                logger.info(f"Removed sandbox container {self.container.short_id}")
            except DockerException as e:
                logger.error(f"Failed to clean up container: {e}")
            self.container = None

        if self.workspace and self.workspace.exists():
            try:
                for item in self.workspace.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        for subitem in item.iterdir():
                            subitem.unlink()
                        item.rmdir()
                self.workspace.rmdir()
                logger.info(f"Removed sandbox workspace at {self.workspace}")
            except OSError as e:
                logger.error(f"Failed to clean up workspace: {e}")
            self.workspace = None
