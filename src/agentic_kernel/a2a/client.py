"""A2A Protocol client implementation.

This module provides a client for interacting with A2A protocol servers,
allowing Agentic Kernel to communicate with other A2A-compatible agents.

Usage:
    ```python
    from agentic_kernel.a2a.client import A2AClient
    
    # Create a client for a specific agent
    client = A2AClient(agent_url="https://example.com", api_key="your-api-key")
    
    # Discover agent capabilities
    agent_card = await client.discover()
    print(f"Connected to agent: {agent_card.name}")
    
    # Send a task
    task = await client.send_task(
        title="Example task",
        description="This is an example task",
    )
    print(f"Task created with ID: {task.id}")
    
    # Get task status
    task_status = await client.get_task(task.id)
    print(f"Task status: {task_status.status}")
    ```
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import urljoin
from uuid import UUID

import aiohttp
from pydantic import HttpUrl, ValidationError

# Use relative import for models within the same package
from .models import (
    AgentCard,
    Message,
    PushNotificationConfig,
    PushNotificationResponse,
    Task,
    TaskListResponse,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TextPart,
)

# Configure logging
logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass


class A2AClient:
    """Client for interacting with A2A protocol servers."""
    
    def __init__(
        self,
        agent_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize the A2A client.
        
        Args:
            agent_url: Base URL of the A2A agent
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.agent_url = agent_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.agent_card: Optional[AgentCard] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication if available."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def _get_url(self, path: str) -> str:
        """Get full URL for a given path."""
        return urljoin(self.agent_url, path)
    
    async def discover(self) -> AgentCard:
        """Discover agent capabilities by fetching the agent card."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._get_url("/.well-known/agent.json"),
                    headers=self._get_headers(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to discover agent: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    self.agent_card = AgentCard.parse_obj(data)
                    return self.agent_card
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error during agent discovery: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid agent card format: {e}")
    
    async def send_task(
        self,
        title: str,
        description: str,
        initial_message: Optional[str] = None,
        skill_name: Optional[str] = None,
        skill_input: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """Send a new task to the agent.
        
        Args:
            title: Title of the task
            description: Description of what the task should accomplish
            initial_message: Optional initial message text
            skill_name: Optional name of the skill to use
            skill_input: Optional input parameters for the skill
            
        Returns:
            The created task
        """
        # Create task request
        request = TaskRequest(
            title=title,
            description=description,
            skill_name=skill_name,
            skill_input=skill_input,
        )
        
        # Add initial message if provided
        if initial_message:
            request.initial_message = Message(
                role="user",
                parts=[TextPart(text=initial_message)],
            )
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self._get_url("/tasks/send"),
                    headers=self._get_headers(),
                    json=request.dict(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to send task: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    task_response = TaskResponse.parse_obj(data)
                    return task_response.task
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error sending task: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid task response format: {e}")
    
    async def get_task(self, task_id: UUID) -> Task:
        """Get information about a task.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            The task information
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._get_url(f"/tasks/get?task_id={task_id}"),
                    headers=self._get_headers(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to get task: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    task_response = TaskResponse.parse_obj(data)
                    return task_response.task
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error getting task: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid task response format: {e}")
    
    async def list_tasks(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[TaskStatus] = None,
    ) -> TaskListResponse:
        """List tasks with optional filtering.
        
        Args:
            page: Page number (1-based)
            page_size: Number of tasks per page
            status: Optional status filter
            
        Returns:
            List of tasks matching the criteria
        """
        params = {
            "page": page,
            "page_size": page_size,
        }
        
        if status:
            params["status"] = status.value
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._get_url("/tasks/list"),
                    headers=self._get_headers(),
                    params=params,
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to list tasks: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    return TaskListResponse.parse_obj(data)
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error listing tasks: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid task list response format: {e}")
    
    async def cancel_task(self, task_id: UUID) -> Task:
        """Cancel a running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            The updated task
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self._get_url(f"/tasks/cancel?task_id={task_id}"),
                    headers=self._get_headers(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to cancel task: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    task_response = TaskResponse.parse_obj(data)
                    return task_response.task
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error cancelling task: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid task response format: {e}")
    
    async def send_subscribe_task(
        self,
        title: str,
        description: str,
        skill_name: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create a task and subscribe to updates (streaming).
        
        Args:
            title: Title of the task
            description: Description of what the task should accomplish
            skill_name: Optional name of the skill to use
            
        Yields:
            Task update events
        """
        params = {
            "title": title,
            "description": description,
        }
        
        if skill_name:
            params["skill_name"] = skill_name
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._get_url("/tasks/sendSubscribe"),
                    headers=self._get_headers(),
                    params=params,
                    timeout=None,  # No timeout for streaming
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to subscribe to task: {response.status} - {error_text}"
                        )
                    
                    # Process Server-Sent Events
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        
                        if not line:
                            continue
                        
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            yield data
                        
                        if line.startswith("event:"):
                            event = line[6:].strip()
                            # You can handle different event types here if needed
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error in task subscription: {e}")
    
    async def set_push_notification(
        self,
        webhook_url: str,
        secret: Optional[str] = None,
        events: Optional[List[str]] = None,
    ) -> PushNotificationResponse:
        """Configure push notifications.
        
        Args:
            webhook_url: URL to receive push notifications
            secret: Optional secret for signing webhook payloads
            events: Optional list of events to receive notifications for
            
        Returns:
            Push notification configuration
        """
        config = PushNotificationConfig(
            webhook_url=webhook_url,
            secret=secret,
        )
        
        if events:
            config.events = events
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self._get_url("/tasks/pushNotification/set"),
                    headers=self._get_headers(),
                    json=config.dict(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to set push notification: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    return PushNotificationResponse.parse_obj(data)
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error setting push notification: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid push notification response format: {e}")
    
    async def get_push_notification(self, config_id: UUID) -> PushNotificationResponse:
        """Get push notification configuration.
        
        Args:
            config_id: ID of the push notification configuration
            
        Returns:
            Push notification configuration
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    self._get_url(f"/tasks/pushNotification/get?config_id={config_id}"),
                    headers=self._get_headers(),
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to get push notification: {response.status} - {error_text}"
                        )
                    
                    data = await response.json()
                    return PushNotificationResponse.parse_obj(data)
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error getting push notification: {e}")
            except ValidationError as e:
                raise A2AClientError(f"Invalid push notification response format: {e}")
    
    async def resubscribe(self, task_id: UUID) -> AsyncGenerator[Dict[str, Any], None]:
        """Resubscribe to a task's updates.
        
        Args:
            task_id: ID of the task to resubscribe to
            
        Yields:
            Task update events
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self._get_url(f"/tasks/resubscribe?task_id={task_id}"),
                    headers=self._get_headers(),
                    timeout=None,  # No timeout for streaming
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise A2AClientError(
                            f"Failed to resubscribe to task: {response.status} - {error_text}"
                        )
                    
                    # Process Server-Sent Events
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        
                        if not line:
                            continue
                        
                        if line.startswith("data:"):
                            data = json.loads(line[5:].strip())
                            yield data
                        
                        if line.startswith("event:"):
                            event = line[6:].strip()
                            # You can handle different event types here if needed
            
            except aiohttp.ClientError as e:
                raise A2AClientError(f"HTTP error in task resubscription: {e}")
