"""Example script demonstrating how to use the memory system programmatically.

This script shows how to:
1. Initialize the memory system components
2. Create and use the MemoryAgent and WebSurferAgent
3. Execute a workflow to search the web and store results in memory
4. Execute a workflow to retrieve information from memory

Run this script with:
    python examples/memory_system_app/example.py
"""

import asyncio
import logging
from typing import Any

from agentic_kernel.agents import MemoryAgent, WebSurferAgent
from agentic_kernel.config import AgentConfig, LLMMapping
from agentic_kernel.memory.manager import MemoryManager
from agentic_kernel.types import Task

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def search_and_memorize(web_agent: WebSurferAgent, memory_agent: MemoryAgent, query: str) -> dict[str, Any]:
    """Search the web and store results in memory.
    
    Args:
        web_agent: The WebSurferAgent to use for searching
        memory_agent: The MemoryAgent to use for storing memories
        query: The search query
        
    Returns:
        The search results
    """
    logger.info(f"Searching for '{query}'...")
    
    # Step 1: Search the web
    search_task = Task(
        description=f"Search web for '{query}'",
        agent_id="web_surfer",
        inputs={"query": query},
    )
    
    search_result = await web_agent.execute(search_task)
    
    if search_result.get("status") != "completed":
        logger.error(f"Search failed: {search_result.get('error', 'Unknown error')}")
        return {"error": search_result.get("error", "Unknown error")}
    
    search_data = search_result.get("results", [])
    logger.info(f"Found {len(search_data)} search results")
    
    # Format search results for storage
    content_to_store = []
    for item in search_data:
        if isinstance(item, dict):
            content_to_store.append({
                "title": item.get("title", "No title"),
                "snippet": item.get("snippet", "No snippet"),
                "url": item.get("url", "No URL"),
            })
        else:
            content_to_store.append(str(item))
    
    # Step 2: Store in memory
    logger.info("Storing search results in memory...")
    
    memory_task = Task(
        description="Store search findings in memory",
        agent_id="memory",
        inputs={
            "content_to_store": content_to_store,
            "memory_topic": query,
            "memory_type": "FACT",
            "tags": ["web_search", query],
        },
    )
    
    memory_result = await memory_agent.execute(memory_task)
    
    if memory_result.get("status") != "completed":
        logger.error(f"Memory storage failed: {memory_result.get('error', 'Unknown error')}")
        return {"error": memory_result.get("error", "Unknown error")}
    
    logger.info(f"Successfully stored search results in memory with ID: {memory_result.get('memory_id')}")
    return {"search_results": search_data, "memory_id": memory_result.get("memory_id")}

async def recall_from_memory(memory_agent: MemoryAgent, query: str) -> dict[str, Any]:
    """Recall information from memory.
    
    Args:
        memory_agent: The MemoryAgent to use for retrieving memories
        query: The memory search query
        
    Returns:
        The retrieved memories
    """
    logger.info(f"Searching memory for '{query}'...")
    
    memory_task = Task(
        description=f"Search memory for '{query}'",
        agent_id="memory",
        inputs={
            "query": query,
            "max_results": 5,
        },
    )
    
    memory_result = await memory_agent.execute(memory_task)
    
    if memory_result.get("status") != "completed":
        logger.error(f"Memory search failed: {memory_result.get('error', 'Unknown error')}")
        return {"error": memory_result.get("error", "Unknown error")}
    
    retrieved_content = memory_result.get("retrieved_content", [])
    
    if not retrieved_content:
        logger.info(f"No memories found for '{query}'.")
    else:
        logger.info(f"Found {len(retrieved_content)} memories for '{query}'.")
        
        # Display the first memory
        if retrieved_content:
            first_memory = retrieved_content[0]
            logger.info(f"First memory: {first_memory.get('content')}")
            
            # Display metadata if available
            metadata = first_memory.get("metadata", {})
            if metadata:
                logger.info(f"Metadata: {metadata}")
    
    return {"memories": retrieved_content}

async def main():
    """Main function demonstrating the memory system workflow."""
    # Initialize memory manager
    memory_manager = MemoryManager(agent_id="example_app")
    await memory_manager.initialize()
    logger.info("Memory manager initialized")
    
    # Create agent configurations
    web_agent_config = AgentConfig(
        name="web_surfer",
        type="WebSurferAgent",
        description="Agent for web searches",
        llm_mapping=LLMMapping(
            model="gemini-1.5-flash",
            endpoint="gemini",
            temperature=0.7,
            max_tokens=2000,
        ),
    )
    
    memory_agent_config = AgentConfig(
        name="memory",
        type="MemoryAgent",
        description="Agent for memory operations",
        llm_mapping=LLMMapping(
            model="gemini-1.5-flash",
            endpoint="gemini",
            temperature=0.7,
            max_tokens=2000,
        ),
    )
    
    # Initialize agents
    web_agent = WebSurferAgent(config=web_agent_config)
    memory_agent = MemoryAgent(config=memory_agent_config, memory_manager=memory_manager)
    await memory_agent.initialize()
    logger.info("Agents initialized")
    
    try:
        # Example 1: Search and memorize
        search_query = "benefits of microservices architecture"
        search_result = await search_and_memorize(web_agent, memory_agent, search_query)
        
        # Wait a moment to ensure memory is stored
        await asyncio.sleep(1)
        
        # Example 2: Recall from memory
        memory_query = "microservices benefits"
        memory_result = await recall_from_memory(memory_agent, memory_query)
        
        logger.info("Memory system workflow completed successfully")
    finally:
        # Clean up resources
        await memory_agent.cleanup()
        await memory_manager.cleanup()
        logger.info("Resources cleaned up")

if __name__ == "__main__":
    asyncio.run(main())