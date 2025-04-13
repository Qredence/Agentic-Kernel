"""A2A Client Implementation

This module implements the client-side of the A2A protocol, providing a framework
for making A2A requests to servers.
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
from pydantic import ValidationError

from .jsonrpc import (
    create_request,
    parse_response,
)
from .types import (
    AgentCard,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskSendParams,
    TaskStatusUpdateEvent,
)

logger = logging.getLogger(__name__)


class A2AClientError(Exception):
    """Base class for A2A client errors."""
    pass


class A2ARequestError(A2AClientError):
    """Error making an A2A request."""
    
    def __init__(self, message: str, status_code: int | None = None, response_text: str | None = None):
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class A2AResponseError(A2AClientError):
    """Error in an A2A response."""
    
    def __init__(self, message: str, error_code: int | None = None, error_data: Any | None = None):
        self.error_code = error_code
        self.error_data = error_data
        super().__init__(message)


class A2AClient:
    """Client for making A2A requests to servers."""
    
    def __init__(
        self,
        base_url: str,
        session: aiohttp.ClientSession | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the A2A client.
        
        Args:
            base_url: The base URL of the A2A server
            session: An existing aiohttp ClientSession to use
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.timeout = timeout
        self._agent_card: AgentCard | None = None
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure that a session exists.
        
        Returns:
            The session
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_agent_card(self, force_refresh: bool = False) -> AgentCard:
        """Get the agent card from the server.
        
        Args:
            force_refresh: Whether to force a refresh of the cached agent card
            
        Returns:
            The agent card
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid
        """
        if self._agent_card is not None and not force_refresh:
            return self._agent_card
        
        session = await self._ensure_session()
        
        try:
            async with session.get(
                f"{self.base_url}/.well-known/agent.json",
                timeout=self.timeout,
            ) as response:
                if response.status != 200:
                    raise A2ARequestError(
                        f"Failed to get agent card: {response.status}",
                        status_code=response.status,
                        response_text=await response.text(),
                    )
                
                try:
                    data = await response.json()
                    self._agent_card = AgentCard(**data)
                    return self._agent_card
                except (json.JSONDecodeError, ValidationError) as e:
                    raise A2AResponseError(f"Invalid agent card: {str(e)}")
        
        except aiohttp.ClientError as e:
            raise A2ARequestError(f"Request error: {str(e)}")
    
    async def _make_request(
        self,
        method: str,
        params: dict[str, Any],
        request_id: str | None = None,
    ) -> Any:
        """Make a JSON-RPC request to the server.
        
        Args:
            method: The method to call
            params: The parameters for the method
            request_id: The request ID (generated if not provided)
            
        Returns:
            The result of the method call
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        request = create_request(method, params, request_id)
        session = await self._ensure_session()
        
        try:
            async with session.post(
                self.base_url,
                json=request.dict(exclude_none=True),
                timeout=self.timeout,
            ) as response:
                if response.status != 200:
                    raise A2ARequestError(
                        f"Request failed: {response.status}",
                        status_code=response.status,
                        response_text=await response.text(),
                    )
                
                try:
                    data = await response.json()
                    jsonrpc_response, error = parse_response(data)
                    
                    if error:
                        raise A2AResponseError(f"Invalid response: {str(error)}")
                    
                    if jsonrpc_response.error:
                        raise A2AResponseError(
                            jsonrpc_response.error.message,
                            error_code=jsonrpc_response.error.code,
                            error_data=jsonrpc_response.error.data,
                        )
                    
                    return jsonrpc_response.result
                
                except json.JSONDecodeError as e:
                    raise A2AResponseError(f"Invalid JSON response: {str(e)}")
        
        except aiohttp.ClientError as e:
            raise A2ARequestError(f"Request error: {str(e)}")
    
    async def _stream_request(
        self,
        method: str,
        params: dict[str, Any],
        request_id: str | None = None,
    ) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        """Make a streaming JSON-RPC request to the server.
        
        Args:
            method: The method to call
            params: The parameters for the method
            request_id: The request ID (generated if not provided)
            
        Yields:
            Task status and artifact update events
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        request = create_request(method, params, request_id)
        session = await self._ensure_session()
        
        try:
            async with session.post(
                self.base_url,
                json=request.dict(exclude_none=True),
                timeout=self.timeout,
            ) as response:
                if response.status != 200:
                    raise A2ARequestError(
                        f"Request failed: {response.status}",
                        status_code=response.status,
                        response_text=await response.text(),
                    )
                
                # Check content type
                content_type = response.headers.get("Content-Type", "")
                if "text/event-stream" not in content_type:
                    raise A2AResponseError(
                        f"Expected SSE response, got {content_type}",
                    )
                
                # Process SSE stream
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith(":"):
                        continue
                    
                    # Parse SSE event
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        
                        try:
                            data = json.loads(data_str)
                            
                            # Check for error
                            if "error" in data:
                                raise A2AResponseError(
                                    data["error"].get("message", "Unknown error"),
                                    error_code=data["error"].get("code"),
                                    error_data=data["error"].get("data"),
                                )
                            
                            # Determine event type
                            if "status" in data:
                                event = TaskStatusUpdateEvent(**data)
                                yield event
                                
                                # If this is the final event, stop
                                if event.final:
                                    break
                            
                            elif "artifact" in data:
                                event = TaskArtifactUpdateEvent(**data)
                                yield event
                            
                            else:
                                logger.warning(f"Unknown event type: {data}")
                        
                        except (json.JSONDecodeError, ValidationError) as e:
                            raise A2AResponseError(f"Invalid event data: {str(e)}")
        
        except aiohttp.ClientError as e:
            raise A2ARequestError(f"Request error: {str(e)}")
    
    # A2A methods
    
    async def tasks_send(self, params: TaskSendParams) -> Task:
        """Send a task to the server.
        
        Args:
            params: The task parameters
            
        Returns:
            The task
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        result = await self._make_request("tasks/send", params.dict(exclude_none=True))
        return Task(**result)
    
    async def tasks_send_subscribe(
        self,
        params: TaskSendParams,
    ) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        """Send a task to the server and subscribe to updates.
        
        Args:
            params: The task parameters
            
        Yields:
            Task status and artifact update events
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        async for event in self._stream_request("tasks/sendSubscribe", params.dict(exclude_none=True)):
            yield event
    
    async def tasks_get(self, task_id: str, history_length: int | None = None) -> Task:
        """Get a task from the server.
        
        Args:
            task_id: The task ID
            history_length: The number of history items to include
            
        Returns:
            The task
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        params = TaskQueryParams(id=task_id, history_length=history_length)
        result = await self._make_request("tasks/get", params.dict(exclude_none=True))
        return Task(**result)
    
    async def tasks_cancel(self, task_id: str) -> Task:
        """Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The updated task
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        params = TaskIdParams(id=task_id)
        result = await self._make_request("tasks/cancel", params.dict(exclude_none=True))
        return Task(**result)
    
    async def tasks_push_notification_set(self, config: TaskPushNotificationConfig) -> dict[str, Any]:
        """Set push notification configuration for a task.
        
        Args:
            config: The push notification configuration
            
        Returns:
            The push notification configuration
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        result = await self._make_request("tasks/pushNotification/set", config.dict(exclude_none=True))
        return result
    
    async def tasks_push_notification_get(self, task_id: str) -> dict[str, Any]:
        """Get push notification configuration for a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The push notification configuration
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        params = TaskIdParams(id=task_id)
        result = await self._make_request("tasks/pushNotification/get", params.dict(exclude_none=True))
        return result
    
    async def tasks_resubscribe(
        self,
        task_id: str,
        history_length: int | None = None,
    ) -> AsyncGenerator[TaskStatusUpdateEvent | TaskArtifactUpdateEvent, None]:
        """Resubscribe to task updates.
        
        Args:
            task_id: The task ID
            history_length: The number of history items to include
            
        Yields:
            Task status and artifact update events
            
        Raises:
            A2ARequestError: If the request fails
            A2AResponseError: If the response is invalid or contains an error
        """
        params = TaskQueryParams(id=task_id, history_length=history_length)
        async for event in self._stream_request("tasks/resubscribe", params.dict(exclude_none=True)):
            yield event