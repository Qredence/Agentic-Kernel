"""Memory Agent for interacting with the memory system.

This agent provides capabilities for storing and retrieving information
from the memory system, allowing agents to maintain context across tasks
and workflow executions.
"""

import logging
from typing import Any

from agentic_kernel.config_types import AgentConfig
from agentic_kernel.memory.manager import MemoryManager
from agentic_kernel.memory.types import MemoryType
from agentic_kernel.types import Task, TaskStatus

from .base import BaseAgent, TaskCapability

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent):
    """Agent for interacting with the memory system.
    
    This agent provides capabilities for:
    - Storing information in memory
    - Retrieving information from memory
    - Managing memory entries
    
    It serves as an interface to the MemoryManager, allowing other agents
    to store and retrieve information across tasks and workflow executions.
    """
    
    def __init__(self, config: AgentConfig, memory_manager: MemoryManager | None = None):
        """Initialize the memory agent.
        
        Args:
            config: Agent configuration
            memory_manager: Optional memory manager instance. If not provided,
                a new one will be created using the agent's ID.
        """
        super().__init__(config)
        self.memory_manager = memory_manager or MemoryManager(agent_id=self.id)
        
    async def initialize(self):
        """Initialize the memory manager."""
        await self.memory_manager.initialize()
        logger.info(f"Memory agent {self.id} initialized with memory manager")
        
    async def cleanup(self):
        """Clean up resources."""
        await self.memory_manager.cleanup()
        logger.info(f"Memory agent {self.id} cleaned up")
        
    async def execute(self, task: Task) -> dict[str, Any]:
        """Execute a memory-related task.
        
        Supported tasks:
        - add_memory: Store information in memory
        - search_memory: Retrieve information from memory
        - forget_memory: Delete a memory entry
        - update_memory: Update an existing memory entry
        
        Args:
            task: The task to execute
            
        Returns:
            Task result
        """
        task_type = task.description.lower()
        
        try:
            if "add" in task_type or "store" in task_type:
                return await self._handle_add_memory(task)
            if "search" in task_type or "retrieve" in task_type or "recall" in task_type:
                return await self._handle_search_memory(task)
            if "forget" in task_type or "delete" in task_type:
                return await self._handle_forget_memory(task)
            if "update" in task_type:
                return await self._handle_update_memory(task)
            logger.warning(f"Unknown memory task type: {task_type}")
            return {
                "status": TaskStatus.FAILED,
                "error": f"Unknown memory task type: {task_type}",
            }
        except Exception as e:
            logger.error(f"Error executing memory task: {e}", exc_info=True)
            return {
                "status": TaskStatus.FAILED,
                "error": str(e),
            }
    
    async def _handle_add_memory(self, task: Task) -> dict[str, Any]:
        """Handle adding a memory.
        
        Expected inputs:
        - content_to_store: The content to store
        - memory_topic: Optional topic for the memory
        - memory_type: Optional memory type (default: FACT)
        - importance: Optional importance score (default: 0.5)
        - context: Optional context
        - metadata: Optional metadata
        - tags: Optional tags
        
        Returns:
            Task result with memory_id
        """
        content = task.inputs.get("content_to_store")
        if not content:
            return {
                "status": TaskStatus.FAILED,
                "error": "No content provided to store in memory",
            }
            
        memory_type_str = task.inputs.get("memory_type", "FACT")
        try:
            memory_type = MemoryType[memory_type_str.upper()]
        except (KeyError, AttributeError):
            memory_type = MemoryType.FACT
            
        importance = float(task.inputs.get("importance", 0.5))
        context = task.inputs.get("context")
        metadata = task.inputs.get("metadata", {})
        
        # Add topic to metadata if provided
        topic = task.inputs.get("memory_topic")
        if topic:
            if not metadata:
                metadata = {}
            metadata["topic"] = topic
            
        tags = task.inputs.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]
            
        memory_id = await self.memory_manager.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            context=context,
            metadata=metadata,
            tags=tags,
        )
        
        logger.info(f"Added memory with ID {memory_id}")
        return {
            "status": TaskStatus.COMPLETED,
            "memory_id": memory_id,
            "memory_add_status": "success",
        }
    
    async def _handle_search_memory(self, task: Task) -> dict[str, Any]:
        """Handle searching memory.
        
        Expected inputs:
        - query: The search query
        - memory_type: Optional memory type filter
        - tags: Optional tags filter
        - min_relevance: Optional minimum relevance score (default: 0.0)
        - max_results: Optional maximum number of results (default: 10)
        
        Returns:
            Task result with retrieved_memories
        """
        query = task.inputs.get("query")
        if not query:
            return {
                "status": TaskStatus.FAILED,
                "error": "No query provided for memory search",
            }
            
        memory_type_str = task.inputs.get("memory_type")
        memory_type = None
        if memory_type_str:
            try:
                memory_type = MemoryType[memory_type_str.upper()]
            except (KeyError, AttributeError):
                pass
                
        tags = task.inputs.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",")]
            
        min_relevance = float(task.inputs.get("min_relevance", 0.0))
        max_results = int(task.inputs.get("max_results", 10))
        
        memories = await self.memory_manager.recall(
            query=query,
            memory_type=memory_type,
            tags=tags,
            min_relevance=min_relevance,
            max_results=max_results,
        )
        
        # Convert memories to a serializable format
        serialized_memories = []
        for memory in memories:
            serialized_memories.append({
                "memory_id": memory.memory_id,
                "content": memory.content,
                "metadata": memory.metadata,
                "relevance": memory.relevance,
                "created_at": str(memory.created_at) if memory.created_at else None,
                "memory_type": memory.memory_type.name if memory.memory_type else None,
                "importance": memory.importance,
                "tags": memory.tags,
            })
        
        logger.info(f"Retrieved {len(serialized_memories)} memories for query '{query}'")
        return {
            "status": TaskStatus.COMPLETED,
            "retrieved_content": serialized_memories,
        }
    
    async def _handle_forget_memory(self, task: Task) -> dict[str, Any]:
        """Handle forgetting a memory.
        
        Expected inputs:
        - memory_id: The ID of the memory to forget
        
        Returns:
            Task result
        """
        memory_id = task.inputs.get("memory_id")
        if not memory_id:
            return {
                "status": TaskStatus.FAILED,
                "error": "No memory_id provided to forget",
            }
            
        await self.memory_manager.forget(memory_id)
        
        logger.info(f"Forgot memory with ID {memory_id}")
        return {
            "status": TaskStatus.COMPLETED,
            "memory_forget_status": "success",
        }
    
    async def _handle_update_memory(self, task: Task) -> dict[str, Any]:
        """Handle updating a memory.
        
        Expected inputs:
        - memory_id: The ID of the memory to update
        - updates: Dictionary of updates to apply
        
        Returns:
            Task result
        """
        memory_id = task.inputs.get("memory_id")
        if not memory_id:
            return {
                "status": TaskStatus.FAILED,
                "error": "No memory_id provided to update",
            }
            
        updates = task.inputs.get("updates")
        if not updates:
            return {
                "status": TaskStatus.FAILED,
                "error": "No updates provided",
            }
            
        await self.memory_manager.update_memory(memory_id, updates)
        
        logger.info(f"Updated memory with ID {memory_id}")
        return {
            "status": TaskStatus.COMPLETED,
            "memory_update_status": "success",
        }
    
    def _get_supported_tasks(self) -> list[TaskCapability]:
        """Get the tasks supported by this agent.
        
        Returns:
            List of supported task capabilities
        """
        return [
            TaskCapability(
                name="add_memory",
                description="Store information in memory",
                parameters={
                    "content_to_store": "The content to store in memory",
                    "memory_topic": "Optional topic for the memory",
                    "memory_type": "Optional memory type (FACT, REFLECTION, PLAN, etc.)",
                    "importance": "Optional importance score (0.0-1.0)",
                    "context": "Optional context for the memory",
                    "metadata": "Optional metadata for the memory",
                    "tags": "Optional tags for the memory",
                },
                required_parameters=["content_to_store"],
            ),
            TaskCapability(
                name="search_memory",
                description="Retrieve information from memory",
                parameters={
                    "query": "The search query",
                    "memory_type": "Optional memory type filter",
                    "tags": "Optional tags filter",
                    "min_relevance": "Optional minimum relevance score (0.0-1.0)",
                    "max_results": "Optional maximum number of results",
                },
                required_parameters=["query"],
            ),
            TaskCapability(
                name="forget_memory",
                description="Delete a memory entry",
                parameters={
                    "memory_id": "The ID of the memory to forget",
                },
                required_parameters=["memory_id"],
            ),
            TaskCapability(
                name="update_memory",
                description="Update an existing memory entry",
                parameters={
                    "memory_id": "The ID of the memory to update",
                    "updates": "Dictionary of updates to apply",
                },
                required_parameters=["memory_id", "updates"],
            ),
        ]