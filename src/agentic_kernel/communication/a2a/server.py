"""A2A Server Implementation

This module implements the server-side of the A2A protocol, providing a framework
for handling A2A requests and responses over HTTP.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import starlette.applications
import starlette.requests
import starlette.responses
import starlette.routing
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .jsonrpc import (
    create_error_response,
    create_success_response,
    parse_request,
)
from .types import (
    A2AErrorCode,
    AgentCard,
    JSONRPCRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskQueryParams,
    TaskSendParams,
    TaskStatusUpdateEvent,
)

logger = logging.getLogger(__name__)


class A2AMethodRegistry:
    """Registry for A2A methods."""
    
    def __init__(self):
        """Initialize the method registry."""
        self.methods: dict[str, Callable] = {}
        self.streaming_methods: set[str] = set()
    
    def register(self, method_name: str, handler: Callable, streaming: bool = False):
        """Register a method handler.
        
        Args:
            method_name: The name of the method
            handler: The handler function
            streaming: Whether the method supports streaming responses
        """
        self.methods[method_name] = handler
        if streaming:
            self.streaming_methods.add(method_name)
    
    def get_handler(self, method_name: str) -> Callable | None:
        """Get the handler for a method.
        
        Args:
            method_name: The name of the method
            
        Returns:
            The handler function, or None if not found
        """
        return self.methods.get(method_name)
    
    def is_streaming(self, method_name: str) -> bool:
        """Check if a method supports streaming responses.
        
        Args:
            method_name: The name of the method
            
        Returns:
            True if the method supports streaming, False otherwise
        """
        return method_name in self.streaming_methods


class A2AServer:
    """Base class for A2A servers."""
    
    def __init__(
        self,
        agent_card: AgentCard,
        host: str = "0.0.0.0",
        port: int = 8000,
        cors_origins: list[str] = None,
        debug: bool = False,
    ):
        """Initialize the A2A server.
        
        Args:
            agent_card: The agent card describing this agent
            host: The host to bind to
            port: The port to bind to
            cors_origins: List of allowed CORS origins
            debug: Whether to enable debug mode
        """
        self.agent_card = agent_card
        self.host = host
        self.port = port
        self.cors_origins = cors_origins or ["*"]
        self.debug = debug
        
        self.registry = A2AMethodRegistry()
        self._setup_default_methods()
        
        # Create the Starlette application
        middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=self.cors_origins,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["Content-Type", "Authorization"],
            ),
        ]
        
        self.app = starlette.applications.Starlette(
            debug=debug,
            middleware=middleware,
            routes=[
                starlette.routing.Route("/.well-known/agent.json", self._handle_agent_card, methods=["GET"]),
                starlette.routing.Route("/", self._handle_jsonrpc, methods=["POST"]),
            ],
        )
    
    def _setup_default_methods(self):
        """Set up default A2A methods."""
        # Register standard A2A methods
        self.registry.register("tasks/send", self.handle_tasks_send)
        self.registry.register("tasks/sendSubscribe", self.handle_tasks_send_subscribe, streaming=True)
        self.registry.register("tasks/get", self.handle_tasks_get)
        self.registry.register("tasks/cancel", self.handle_tasks_cancel)
        self.registry.register("tasks/pushNotification/set", self.handle_tasks_push_notification_set)
        self.registry.register("tasks/pushNotification/get", self.handle_tasks_push_notification_get)
        self.registry.register("tasks/resubscribe", self.handle_tasks_resubscribe, streaming=True)
    
    async def _handle_agent_card(self, request: starlette.requests.Request) -> starlette.responses.JSONResponse:
        """Handle requests for the agent card.
        
        Args:
            request: The HTTP request
            
        Returns:
            A JSON response containing the agent card
        """
        return starlette.responses.JSONResponse(self.agent_card.dict())
    
    async def _handle_jsonrpc(self, request: starlette.requests.Request) -> starlette.responses.Response:
        """Handle JSON-RPC requests.
        
        Args:
            request: The HTTP request
            
        Returns:
            An HTTP response
        """
        # Parse the request body
        try:
            body = await request.body()
            jsonrpc_request, error_response = parse_request(body)
            
            if error_response:
                return starlette.responses.JSONResponse(
                    error_response.dict(exclude_none=True),
                    status_code=400,
                )
            
            if not jsonrpc_request:
                return starlette.responses.JSONResponse(
                    create_error_response(
                        A2AErrorCode.INVALID_REQUEST,
                        "Invalid request",
                    ).dict(exclude_none=True),
                    status_code=400,
                )
            
            # Get the method handler
            method_name = jsonrpc_request.method
            handler = self.registry.get_handler(method_name)
            
            if not handler:
                return starlette.responses.JSONResponse(
                    create_error_response(
                        A2AErrorCode.METHOD_NOT_FOUND,
                        f"Method not found: {method_name}",
                        request_id=jsonrpc_request.id,
                    ).dict(exclude_none=True),
                    status_code=404,
                )
            
            # Check if this is a streaming method
            is_streaming = self.registry.is_streaming(method_name)
            
            # Handle the request
            try:
                if is_streaming:
                    # For streaming methods, return an SSE response
                    return await self._handle_streaming_method(jsonrpc_request, handler)
                # For regular methods, return a JSON response
                return await self._handle_regular_method(jsonrpc_request, handler)
            
            except Exception as e:
                logger.exception(f"Error handling method {method_name}: {e}")
                return starlette.responses.JSONResponse(
                    create_error_response(
                        A2AErrorCode.INTERNAL_ERROR,
                        f"Internal error: {str(e)}",
                        request_id=jsonrpc_request.id,
                    ).dict(exclude_none=True),
                    status_code=500,
                )
        
        except Exception as e:
            logger.exception(f"Error handling JSON-RPC request: {e}")
            return starlette.responses.JSONResponse(
                create_error_response(
                    A2AErrorCode.INTERNAL_ERROR,
                    f"Internal error: {str(e)}",
                ).dict(exclude_none=True),
                status_code=500,
            )
    
    async def _handle_regular_method(
        self,
        request: JSONRPCRequest,
        handler: Callable,
    ) -> starlette.responses.JSONResponse:
        """Handle a regular (non-streaming) method.
        
        Args:
            request: The JSON-RPC request
            handler: The method handler
            
        Returns:
            A JSON response
        """
        # Call the handler
        result = await handler(request.params)
        
        # Create the response
        response = create_success_response(result, request.id)
        
        # Return the response
        return starlette.responses.JSONResponse(response.dict(exclude_none=True))
    
    async def _handle_streaming_method(
        self,
        request: JSONRPCRequest,
        handler: Callable,
    ) -> starlette.responses.StreamingResponse:
        """Handle a streaming method.
        
        Args:
            request: The JSON-RPC request
            handler: The method handler
            
        Returns:
            An SSE streaming response
        """
        # Create a queue for the events
        queue = asyncio.Queue()
        
        # Start the handler in a background task
        asyncio.create_task(self._run_streaming_handler(request, handler, queue))
        
        # Return a streaming response
        async def event_generator():
            while True:
                event = await queue.get()
                if event is None:
                    break
                
                event_json = json.dumps(event)
                yield f"data: {event_json}\n\n"
        
        return starlette.responses.StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    
    async def _run_streaming_handler(
        self,
        request: JSONRPCRequest,
        handler: Callable,
        queue: asyncio.Queue,
    ):
        """Run a streaming handler and put events in the queue.
        
        Args:
            request: The JSON-RPC request
            handler: The method handler
            queue: The queue to put events in
        """
        try:
            # Call the handler
            async for event in handler(request.params):
                # Put the event in the queue
                await queue.put(event.dict(exclude_none=True))
                
                # If this is the final event, stop
                if getattr(event, "final", False):
                    break
            
            # Signal the end of the stream
            await queue.put(None)
        
        except Exception as e:
            logger.exception(f"Error in streaming handler: {e}")
            
            # Put an error event in the queue
            error_event = {
                "error": {
                    "code": A2AErrorCode.INTERNAL_ERROR,
                    "message": f"Internal error: {str(e)}",
                },
                "id": request.id,
                "jsonrpc": "2.0",
                "final": True,
            }
            
            await queue.put(error_event)
            await queue.put(None)
    
    def run(self):
        """Run the server."""
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    # A2A method handlers
    
    async def handle_tasks_send(self, params: dict[str, Any]) -> Task:
        """Handle the tasks/send method.
        
        Args:
            params: The method parameters
            
        Returns:
            The task
        """
        # Parse the parameters
        send_params = TaskSendParams(**params)
        
        # Process the task
        task = await self.process_task(send_params)
        
        return task
    
    async def handle_tasks_send_subscribe(self, params: dict[str, Any]):
        """Handle the tasks/sendSubscribe method.
        
        Args:
            params: The method parameters
            
        Yields:
            Task status and artifact update events
        """
        # Parse the parameters
        send_params = TaskSendParams(**params)
        
        # Process the task and get the initial status
        task = await self.process_task(send_params)
        
        # Yield the initial status
        yield TaskStatusUpdateEvent(
            id=task.id,
            status=task.status,
            final=task.status.state in [
                "completed",
                "canceled",
                "failed",
            ],
        )
        
        # If there are artifacts, yield them
        if task.artifacts:
            for artifact in task.artifacts:
                yield TaskArtifactUpdateEvent(
                    id=task.id,
                    artifact=artifact,
                    final=False,
                )
        
        # If the task is already in a final state, we're done
        if task.status.state in ["completed", "canceled", "failed"]:
            return
        
        # Otherwise, subscribe to task updates
        async for event in self.subscribe_to_task(task.id):
            yield event
    
    async def handle_tasks_get(self, params: dict[str, Any]) -> Task:
        """Handle the tasks/get method.
        
        Args:
            params: The method parameters
            
        Returns:
            The task
        """
        # Parse the parameters
        query_params = TaskQueryParams(**params)
        
        # Get the task
        task = await self.get_task(query_params.id, query_params.history_length)
        
        return task
    
    async def handle_tasks_cancel(self, params: dict[str, Any]) -> Task:
        """Handle the tasks/cancel method.
        
        Args:
            params: The method parameters
            
        Returns:
            The updated task
        """
        # Parse the parameters
        id_params = TaskIdParams(**params)
        
        # Cancel the task
        task = await self.cancel_task(id_params.id)
        
        return task
    
    async def handle_tasks_push_notification_set(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the tasks/pushNotification/set method.
        
        Args:
            params: The method parameters
            
        Returns:
            The push notification configuration
        """
        # This is a placeholder - subclasses should implement this
        raise NotImplementedError("Push notifications are not supported")
    
    async def handle_tasks_push_notification_get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle the tasks/pushNotification/get method.
        
        Args:
            params: The method parameters
            
        Returns:
            The push notification configuration
        """
        # This is a placeholder - subclasses should implement this
        raise NotImplementedError("Push notifications are not supported")
    
    async def handle_tasks_resubscribe(self, params: dict[str, Any]):
        """Handle the tasks/resubscribe method.
        
        Args:
            params: The method parameters
            
        Yields:
            Task status and artifact update events
        """
        # Parse the parameters
        query_params = TaskQueryParams(**params)
        
        # Get the task
        task = await self.get_task(query_params.id, query_params.history_length)
        
        # Yield the current status
        yield TaskStatusUpdateEvent(
            id=task.id,
            status=task.status,
            final=task.status.state in [
                "completed",
                "canceled",
                "failed",
            ],
        )
        
        # If there are artifacts, yield them
        if task.artifacts:
            for artifact in task.artifacts:
                yield TaskArtifactUpdateEvent(
                    id=task.id,
                    artifact=artifact,
                    final=False,
                )
        
        # If the task is already in a final state, we're done
        if task.status.state in ["completed", "canceled", "failed"]:
            return
        
        # Otherwise, subscribe to task updates
        async for event in self.subscribe_to_task(task.id):
            yield event
    
    # Methods to be implemented by subclasses
    
    async def process_task(self, params: TaskSendParams) -> Task:
        """Process a task.
        
        Args:
            params: The task parameters
            
        Returns:
            The task
        """
        raise NotImplementedError("Subclasses must implement process_task")
    
    async def get_task(self, task_id: str, history_length: int | None = None) -> Task:
        """Get a task.
        
        Args:
            task_id: The task ID
            history_length: The number of history items to include
            
        Returns:
            The task
        """
        raise NotImplementedError("Subclasses must implement get_task")
    
    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a task.
        
        Args:
            task_id: The task ID
            
        Returns:
            The updated task
        """
        raise NotImplementedError("Subclasses must implement cancel_task")
    
    async def subscribe_to_task(self, task_id: str):
        """Subscribe to task updates.
        
        Args:
            task_id: The task ID
            
        Yields:
            Task status and artifact update events
        """
        raise NotImplementedError("Subclasses must implement subscribe_to_task")