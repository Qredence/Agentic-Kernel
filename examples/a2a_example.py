"""Example of using the A2A protocol implementation.

This script demonstrates how to:
1. Start an A2A protocol server
2. Connect to it with an A2A client
3. Send tasks and receive responses

Usage:
    ```bash
    # Run the example
    python examples/a2a_example.py
    ```
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check for Gemini API Key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    print("Please set it in a .env file or in your environment.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Import A2A components
from src.agentic_kernel.a2a.client import A2AClient
from src.agentic_kernel.a2a.server import run_server


async def run_client_example():
    """Run the A2A client example."""
    print("\n=== A2A Client Example ===\n")
    
    # Create an A2A client
    client = A2AClient(agent_url="http://localhost:8080")
    
    # Discover agent capabilities
    print("Discovering agent capabilities...")
    agent_card = await client.discover()
    print(f"Connected to agent: {agent_card.name} ({agent_card.version})")
    print(f"Description: {agent_card.description}")
    print(f"Skills: {[skill.name for skill in agent_card.skills]}")
    
    # Send a task
    print("\nSending a task...")
    task = await client.send_task(
        title="Example task",
        description="Tell me a short joke about programming",
    )
    print(f"Task created with ID: {task.id}")
    
    # Poll for task completion
    print("\nWaiting for task completion...")
    while True:
        task = await client.get_task(task.id)
        print(f"Task status: {task.status}")
        
        if task.status in ["completed", "failed", "cancelled"]:
            break
        
        await asyncio.sleep(1)
    
    # Display the result
    print("\nTask completed!")
    if task.messages and len(task.messages) > 1:
        # The last message should be from the agent
        agent_message = task.messages[-1]
        print("\nAgent response:")
        for part in agent_message.parts:
            if hasattr(part, "text"):
                print(f"\n{part.text}")
    
    print("\n=== Example Complete ===\n")


def main():
    """Run the A2A example."""
    print("Starting A2A server in a separate process...")
    
    # Start the server in a separate process
    import multiprocessing
    server_process = multiprocessing.Process(target=run_server, args=("localhost", 8080))
    server_process.start()
    
    # Wait for the server to start
    print("Waiting for server to start...")
    import time
    time.sleep(3)
    
    # Run the client example
    try:
        asyncio.run(run_client_example())
    except KeyboardInterrupt:
        print("\nExample interrupted by user.")
    except Exception as e:
        print(f"\nError in example: {e}")
    finally:
        # Terminate the server process
        print("Shutting down server...")
        server_process.terminate()
        server_process.join()
        print("Server shut down.")


if __name__ == "__main__":
    main()
