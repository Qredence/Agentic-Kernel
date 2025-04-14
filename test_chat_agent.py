"""Test script for the ChatAgent.

This script initializes a ChatAgent and tests basic functionality.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check for Gemini API Key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    print("ERROR: GEMINI_API_KEY environment variable not set.")
    print("Please set it in a .env file or in your environment.")
    exit(1)
else:
    print("GEMINI_API_KEY found.")

# Import after checking for API key
from src.agentic_kernel.agents.chat_agent import ChatAgent
from src.agentic_kernel.config import ConfigLoader, AgentConfig, LLMMapping

# Initialize configuration
config_loader = ConfigLoader()

# Create agent config
agent_config = AgentConfig(
    name="test_chat",
    type="ChatAgent",
    description="Test chat agent",
    llm_mapping=LLMMapping(
        model="gemini-1.5-flash",
        endpoint="gemini",
        temperature=0.7,
        max_tokens=2000,
    ),
)

# Initialize chat agent
print("Initializing ChatAgent...")
agent = ChatAgent(
    config=agent_config,
    config_loader=config_loader,
)
print("ChatAgent initialized successfully.")

# Test get_capabilities
print("\nTesting get_capabilities():")
capabilities = agent.get_capabilities()
print(f"Agent type: {capabilities['type']}")
print(f"Supported tasks: {list(capabilities['supported_tasks'].keys())}")

# Test chat functionality
async def test_chat():
    print("\nTesting chat functionality:")
    print("Sending message: 'Hello, how are you?'")
    
    response_chunks = []
    async for chunk in agent.handle_message("Hello, how are you?"):
        response_chunks.append(chunk)
        print(f"Received chunk: {chunk}")
    
    complete_response = "".join(response_chunks)
    print(f"\nComplete response: {complete_response}")

# Run the async test
if __name__ == "__main__":
    print("\nRunning chat test...")
    asyncio.run(test_chat())
    print("\nTest completed successfully.")
