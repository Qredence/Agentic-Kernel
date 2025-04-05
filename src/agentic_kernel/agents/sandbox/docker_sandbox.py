"""Docker-based sandbox implementation for secure command execution."""

import asyncio
import os
import json
import uuid
from typing import Dict, Any, Optional, List

from .base import Sandbox


class DockerSandbox(Sandbox):
    """Docker-based sandbox implementation for secure command execution.
    
    This sandbox creates a Docker container for executing commands in an isolated
    environment. It provides security through containerization and resource limits.
    """
    
    def __init__(
        self,
        image: str = "alpine:latest",
        container_name_prefix: str = "agentic_kernel_sandbox_",
        network: str = "none",
        resource_limits: Optional[Dict[str, Any]] = None,
        volumes: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        working_dir: str = "/workspace",
        read_only: bool = True,
        auto_remove: bool = True
    ):
        """Initialize the Docker sandbox.
        
        Args:
            image: Docker image to use
            container_name_prefix: Prefix for container names
            network: Docker network configuration ("none" for no network access)
            resource_limits: Container resource limits (memory, CPU)
            volumes: Volume mount specifications
            environment: Environment variables
            working_dir: Default working directory in the container
            read_only: Whether the container filesystem should be read-only
            auto_remove: Whether to automatically remove the container when stopped
        """
        self.image = image
        self.container_name = f"{container_name_prefix}{uuid.uuid4().hex[:8]}"
        self.network = network
        self.resource_limits = resource_limits or {
            "memory": "512m",
            "cpu-shares": 1024,
            "pids-limit": 100
        }
        self.volumes = volumes or []
        self.environment = environment or {}
        self.default_working_dir = working_dir
        self.read_only = read_only
        self.auto_remove = auto_remove
        self._container_id = None
        self._running = False
    
    async def execute_command(
        self,
        command: str,
        timeout: int = 30,
        working_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a command within the Docker container.
        
        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds
            working_dir: Working directory for command execution
            
        Returns:
            Dictionary with status, output, and error
        """
        if not self._running:
            started = await self.ensure_started()
            if not started:
                return {"status": 1, "output": "", "error": "Failed to start sandbox container"}
        
        working_dir = working_dir or self.default_working_dir
        
        # Prepare docker exec command
        exec_cmd = [
            "docker", "exec",
            "--workdir", working_dir
        ]
        
        # Add environment variables if any
        for key, value in self.environment.items():
            exec_cmd.extend(["-e", f"{key}={value}"])
        
        # Add container ID and the actual command
        exec_cmd.append(self.container_name)
        
        # For complex commands, use sh -c
        exec_cmd.extend(["sh", "-c", command])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except:
                    pass
                return {
                    "status": 1,
                    "output": "",
                    "error": f"Command timed out after {timeout} seconds"
                }
            
            return {
                "status": process.returncode,
                "output": stdout.decode('utf-8', errors='replace'),
                "error": stderr.decode('utf-8', errors='replace')
            }
        
        except Exception as e:
            return {
                "status": 1,
                "output": "",
                "error": f"Error executing command: {str(e)}"
            }
    
    async def ensure_started(self) -> bool:
        """Ensure the Docker container is started.
        
        Returns:
            True if the container is successfully started
        """
        if self._running:
            return True
        
        # Check if container already exists
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.ID}}",
            stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        existing_container = stdout.decode().strip()
        
        if existing_container:
            # Remove existing container
            process = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", self.container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        
        # Build docker run command
        run_cmd = [
            "docker", "run",
            "-d",  # Detached mode
            "--name", self.container_name,
            "--network", self.network,
        ]
        
        # Add resource limits
        for key, value in self.resource_limits.items():
            run_cmd.extend([f"--{key}", str(value)])
        
        # Add volumes
        for volume in self.volumes:
            run_cmd.extend(["-v", volume])
        
        # Add environment variables
        for key, value in self.environment.items():
            run_cmd.extend(["-e", f"{key}={value}"])
        
        # Add working directory
        run_cmd.extend(["-w", self.default_working_dir])
        
        # Add read-only flag if enabled
        if self.read_only:
            run_cmd.append("--read-only")
        
        # Add auto-remove flag if enabled
        if self.auto_remove:
            run_cmd.append("--rm")
        
        # Add image name and default command
        run_cmd.append(self.image)
        run_cmd.extend(["sleep", "infinity"])  # Keep container running
        
        try:
            process = await asyncio.create_subprocess_exec(
                *run_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error = stderr.decode('utf-8', errors='replace')
                print(f"Failed to start container: {error}")
                return False
            
            # Get container ID
            self._container_id = stdout.decode().strip()
            self._running = True
            
            # Create workspace directory if it doesn't exist
            mkdir_process = await asyncio.create_subprocess_exec(
                "docker", "exec", self.container_name, "mkdir", "-p", self.default_working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await mkdir_process.communicate()
            
            return True
            
        except Exception as e:
            print(f"Error starting container: {str(e)}")
            return False
    
    async def cleanup(self) -> None:
        """Stop and remove the Docker container."""
        if not self._running:
            return
        
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "stop", self.container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if not self.auto_remove:
                process = await asyncio.create_subprocess_exec(
                    "docker", "rm", self.container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            self._running = False
            self._container_id = None
            
        except Exception as e:
            print(f"Error cleaning up container: {str(e)}")
    
    async def reset(self) -> bool:
        """Reset the Docker container by stopping and starting a new one.
        
        Returns:
            True if the container was successfully reset
        """
        await self.cleanup()
        return await self.ensure_started()
    
    @property
    def is_running(self) -> bool:
        """Check if the Docker container is currently running.
        
        Returns:
            True if the container is running
        """
        return self._running
    
    async def check_running_status(self) -> bool:
        """Check if the container is actually running using Docker ps.
        
        Returns:
            True if the container is running according to Docker
        """
        process = await asyncio.create_subprocess_exec(
            "docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.ID}}",
            stdout=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        return bool(stdout.decode().strip()) 