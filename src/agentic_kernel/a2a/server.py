"""A2A Protocol server implementation.

This module provides a FastAPI server that implements the A2A protocol endpoints,
allowing other agents to discover and interact with Agentic Kernel agents.

The server exposes the following endpoints:
- /.well-known/agent.json: Agent discovery endpoint
- /tasks/send: Create a new task
- /tasks/get: Get information about a task
- /tasks/sendSubscribe: Create a task and subscribe to updates (streaming)
- /tasks/cancel: Cancel a running task
- /tasks/pushNotification/set: Configure push notifications
- /tasks/pushNotification/get: Get push notification configuration
- /tasks/resubscribe: Resubscribe to a task's updates

Usage:
    ```python
    from agentic_kernel.a2a.server import create_app
    
    app = create_app()
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
    ```
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from sse_starlette.sse import EventSourceResponse

from ..agents.chat_agent import ChatAgent
from ..config import ConfigLoader
from .models import (
    AgentCard,
    AuthConfig,
    AuthType,
    Message,
    PushNotificationConfig,
    PushNotificationResponse,
    SkillDefinition,
    Task,
    TaskListResponse,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TextPart,
)

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for tasks and push notification configs
# In a production environment, this would be replaced with a database
tasks: Dict[UUID, Task] = {}
push_configs: Dict[UUID, PushNotificationConfig] = {}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Agentic Kernel A2A API",
        description="A2A Protocol implementation for Agentic Kernel",
        version="0.1.0",
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Load configuration
    config_loader = ConfigLoader()
    
    # Define agent card
    agent_card = AgentCard(
        name="Agentic Kernel",
        description="An agent framework for building autonomous agent systems",
        version="0.1.0",
        api_endpoint=HttpUrl("http://localhost:8080"),
        auth=AuthConfig(
            type=AuthType.API_KEY,
            instructions="Provide API key in the Authorization header as 'Bearer <api_key>'",
        ),
        skills=[
            SkillDefinition(
                name="chat",
                description="General chat capability",
            ),
        ],
        supports_streaming=True,
        supports_push_notifications=True,
    )
    
    @app.get("/.well-known/agent.json")
    async def get_agent_card() -> AgentCard:
        """Return the agent card for discovery."""
        return agent_card
    
    @app.post("/tasks/send")
    async def send_task(task_request: TaskRequest) -> TaskResponse:
        """Create a new task."""
        # Create a new task
        task = Task(
            title=task_request.title,
            description=task_request.description,
            skill_name=task_request.skill_name,
            skill_input=task_request.skill_input,
        )
        
        # Add initial message if provided
        if task_request.initial_message:
            task.messages.append(task_request.initial_message)
        
        # Store the task
        tasks[task.id] = task
        
        # Process the task asynchronously
        asyncio.create_task(process_task(task.id))
        
        return TaskResponse(task=task)
    
    @app.get("/tasks/get")
    async def get_task(task_id: UUID) -> TaskResponse:
        """Get information about a task."""
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found",
            )
        
        return TaskResponse(task=tasks[task_id])
    
    @app.get("/tasks/list")
    async def list_tasks(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=100),
        status: Optional[TaskStatus] = None,
    ) -> TaskListResponse:
        """List tasks with optional filtering."""
        filtered_tasks = list(tasks.values())
        
        # Filter by status if provided
        if status:
            filtered_tasks = [task for task in filtered_tasks if task.status == status]
        
        # Sort by created_at (newest first)
        filtered_tasks.sort(key=lambda task: task.created_at, reverse=True)
        
        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tasks = filtered_tasks[start_idx:end_idx]
        
        return TaskListResponse(
            tasks=paginated_tasks,
            total=len(filtered_tasks),
            page=page,
            page_size=page_size,
        )
    
    @app.post("/tasks/cancel")
    async def cancel_task(task_id: UUID) -> TaskResponse:
        """Cancel a running task."""
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found",
            )
        
        task = tasks[task_id]
        
        # Only cancel if the task is not already completed, failed, or cancelled
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.utcnow()
            task.completed_at = datetime.utcnow()
        
        return TaskResponse(task=task)
    
    @app.get("/tasks/sendSubscribe")
    async def send_subscribe_task(
        request: Request,
        title: str,
        description: str,
        skill_name: Optional[str] = None,
    ) -> EventSourceResponse:
        """Create a task and subscribe to updates (streaming)."""
        # Create a new task
        task = Task(
            title=title,
            description=description,
            skill_name=skill_name,
        )
        
        # Store the task
        tasks[task.id] = task
        
        # Define the event generator
        async def event_generator():
            # Send initial task state
            yield {
                "event": "task_created",
                "data": task.json(),
            }
            
            # Start processing the task
            asyncio.create_task(process_task(task.id, streaming=True))
            
            # Keep the connection open until the client disconnects or the task completes
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from task {task.id}")
                    break
                
                # Check if the task has completed or failed
                current_task = tasks[task.id]
                if current_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    yield {
                        "event": "task_completed",
                        "data": current_task.json(),
                    }
                    break
                
                # Wait before checking again
                await asyncio.sleep(0.1)
        
        return EventSourceResponse(event_generator())
    
    @app.post("/tasks/pushNotification/set")
    async def set_push_notification(config: PushNotificationConfig) -> PushNotificationResponse:
        """Configure push notifications."""
        response = PushNotificationResponse(config=config)
        push_configs[response.id] = config
        return response
    
    @app.get("/tasks/pushNotification/get")
    async def get_push_notification(config_id: UUID) -> PushNotificationResponse:
        """Get push notification configuration."""
        if config_id not in push_configs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Push notification config with ID {config_id} not found",
            )
        
        return PushNotificationResponse(id=config_id, config=push_configs[config_id])
    
    @app.post("/tasks/resubscribe")
    async def resubscribe(request: Request, task_id: UUID) -> EventSourceResponse:
        """Resubscribe to a task's updates."""
        if task_id not in tasks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found",
            )
        
        task = tasks[task_id]
        
        # Define the event generator
        async def event_generator():
            # Send current task state
            yield {
                "event": "task_state",
                "data": task.json(),
            }
            
            # Keep the connection open until the client disconnects or the task completes
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from task {task_id}")
                    break
                
                # Check if the task has completed or failed
                current_task = tasks[task_id]
                if current_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if current_task.status != task.status:
                        yield {
                            "event": "task_completed",
                            "data": current_task.json(),
                        }
                    break
                
                # Wait before checking again
                await asyncio.sleep(0.1)
        
        return EventSourceResponse(event_generator())
    
    return app


async def process_task(task_id: UUID, streaming: bool = False) -> None:
    """Process a task asynchronously.
    
    This function simulates task processing with the ChatAgent.
    In a real implementation, this would delegate to the appropriate agent
    based on the task's skill_name.
    
    Args:
        task_id: The ID of the task to process
        streaming: Whether to stream updates during processing
    """
    task = tasks[task_id]
    
    # Update task status to working
    task.status = TaskStatus.WORKING
    task.updated_at = datetime.utcnow()
    
    try:
        # Initialize the chat agent
        config_loader = ConfigLoader()
        agent = ChatAgent(
            config=config_loader.get_agent_config("chat"),
            config_loader=config_loader,
        )
        
        # Get the task description or initial message
        prompt = task.description
        if not prompt:
            if task.messages and len(task.messages) > 0:
                # Use the text from the first message if available
                for part in task.messages[0].parts:
                    if hasattr(part, "text"):
                        prompt = part.text
                        break
            else:
                # Fallback if no description or message text is found
                prompt = "Default prompt: Respond to the task."

        # Process with the agent
        response_chunks = []
        async for chunk in agent.handle_message(prompt):
            response_chunks.append(chunk)
            
            # If streaming, update the task with the current partial response
            if streaming and len(response_chunks) % 5 == 0:  # Update every 5 chunks
                current_response = "".join(response_chunks)
                # Add a message from the agent with the current response
                task.messages.append(
                    Message(
                        role="agent",
                        parts=[TextPart(text=current_response)],
                    )
                )
                task.updated_at = datetime.utcnow()
        
        # Combine all chunks for the final response
        final_response = "".join(response_chunks)
        
        # Update the task with the final response
        task.messages.append(
            Message(
                role="agent",
                parts=[TextPart(text=final_response)],
            )
        )
        
        # Mark the task as completed
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.utcnow()
        task.completed_at = datetime.utcnow()
        
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        
        # Mark the task as failed
        task.status = TaskStatus.FAILED
        task.error = str(e)
        task.updated_at = datetime.utcnow()
        task.completed_at = datetime.utcnow()


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Run the A2A server."""
    app = create_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
