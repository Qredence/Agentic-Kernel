"""Simple A2A Protocol Example

This script demonstrates how to use the A2A protocol implementation.
It creates a simple A2A server and client, and shows how to send tasks,
get task status and artifacts, and use streaming for real-time updates.
"""

import asyncio
import logging

from ..client import A2AClient
from ..simple_server import create_simple_server
from ..task import InMemoryTaskManager
from ..types import (
    Message,
    TaskArtifactUpdateEvent,
    TaskSendParams,
    TaskStatusUpdateEvent,
    TextPart,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_server(host: str = "localhost", port: int = 8000):
    """Run the A2A server.
    
    Args:
        host: The host to bind to
        port: The port to bind to
    """
    # Create a task manager
    task_manager = InMemoryTaskManager()
    
    # Create a simple A2A server
    server = create_simple_server(
        name="SimpleEchoAgent",
        description="A simple A2A server that echoes messages",
        version="1.0.0",
        task_manager=task_manager,
        host=host,
        port=port,
        debug=True,
    )
    
    # Run the server
    logger.info(f"Starting A2A server at http://{host}:{port}")
    server.run()


async def run_client(host: str = "localhost", port: int = 8000):
    """Run the A2A client.
    
    Args:
        host: The server host
        port: The server port
    """
    # Create an A2A client
    client = A2AClient(f"http://{host}:{port}")
    
    try:
        # Get the agent card
        logger.info("Getting agent card...")
        agent_card = await client.get_agent_card()
        logger.info(f"Agent name: {agent_card.name}")
        logger.info(f"Agent description: {agent_card.description}")
        logger.info(f"Agent version: {agent_card.version}")
        logger.info(f"Agent capabilities: {agent_card.capabilities}")
        logger.info(f"Agent skills: {[skill.name for skill in agent_card.skills]}")
        
        # Send a task
        logger.info("Sending task...")
        task_params = TaskSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Hello, A2A!",
                    ),
                ],
            ),
        )
        task = await client.tasks_send(task_params)
        logger.info(f"Task ID: {task.id}")
        logger.info(f"Task status: {task.status.state}")
        
        # Get the task
        logger.info("Getting task...")
        task = await client.tasks_get(task.id)
        logger.info(f"Task status: {task.status.state}")
        
        if task.artifacts:
            logger.info(f"Task artifacts: {len(task.artifacts)}")
            for artifact in task.artifacts:
                logger.info(f"Artifact name: {artifact.name}")
                logger.info(f"Artifact description: {artifact.description}")
                for part in artifact.parts:
                    if part.type == "text":
                        logger.info(f"Artifact text: {part.text}")
        
        # Send a task with streaming
        logger.info("Sending task with streaming...")
        task_params = TaskSendParams(
            message=Message(
                role="user",
                parts=[
                    TextPart(
                        type="text",
                        text="Hello, A2A with streaming!",
                    ),
                ],
            ),
        )
        
        async for event in client.tasks_send_subscribe(task_params):
            if isinstance(event, TaskStatusUpdateEvent):
                logger.info(f"Task status update: {event.status.state}")
                if event.final:
                    logger.info("Final status update received")
            elif isinstance(event, TaskArtifactUpdateEvent):
                logger.info(f"Task artifact update: {event.artifact.name}")
                for part in event.artifact.parts:
                    if part.type == "text":
                        logger.info(f"Artifact text: {part.text}")
    
    finally:
        # Close the client
        await client.close()


async def main():
    """Run the example."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Simple A2A Protocol Example")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--mode", choices=["server", "client"], required=True, help="Run mode")
    args = parser.parse_args()
    
    # Run in the specified mode
    if args.mode == "server":
        await run_server(args.host, args.port)
    else:
        await run_client(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())