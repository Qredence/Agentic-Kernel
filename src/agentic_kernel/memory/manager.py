"""Memory manager module for managing agent memories."""

import asyncio
from typing import Dict, List, Optional, Any
import logging
from .types import MemoryEntry, MemoryType, MemoryStats, MemorySearchResult
from .embeddings import EmbeddingService, EmbeddingConfig
from .persistence import PostgresConfig, PostgresMemoryStore, MigrationManager
import asyncpg
import os

logger = logging.getLogger(__name__)


class MemoryManager:
    """High-level memory management for agents."""

    def __init__(
        self,
        agent_id: str,
        embedding_config: Optional[EmbeddingConfig] = None,
        postgres_config: Optional[PostgresConfig] = None,
    ):
        """Initialize the memory manager.

        Args:
            agent_id: ID of the agent this manager belongs to
            embedding_config: Optional configuration for embeddings service
            postgres_config: Optional configuration for PostgreSQL connection
        """
        self.agent_id = agent_id

        # Initialize embedding service
        if embedding_config is None:
            embedding_config = EmbeddingConfig(
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version="2024-02-15-preview",
                deployment_name="text-embedding-3-small",
                batch_size=16,
                cache_embeddings=True,
            )
        self._embedding_service = EmbeddingService(embedding_config)

        # Initialize PostgreSQL connection
        if postgres_config is None:
            postgres_config = PostgresConfig(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "agentic_kernel"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            )
        self._postgres_config = postgres_config
        self._pool: Optional[asyncpg.Pool] = None
        self._store: Optional[PostgresMemoryStore] = None

    async def initialize(self):
        """Initialize the memory manager."""
        # Create connection pool
        self._pool = await asyncpg.create_pool(
            host=self._postgres_config.host,
            port=self._postgres_config.port,
            database=self._postgres_config.database,
            user=self._postgres_config.user,
            password=self._postgres_config.password,
            min_size=1,
            max_size=10,
        )

        # Initialize database schema
        migration_manager = MigrationManager(self._pool)
        await migration_manager.initialize()

        # Create memory store
        self._store = PostgresMemoryStore(self._embedding_service, self._pool)
        await self._store.start()

    async def cleanup(self):
        """Clean up resources."""
        if self._store:
            await self._store.stop()
        if self._pool:
            await self._pool.close()

    async def remember(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        shared_with: Optional[List[str]] = None,
    ) -> str:
        """Store a new memory.

        Args:
            content: Content of the memory
            memory_type: Type of memory
            importance: Importance score (0-1)
            context: Optional context string
            metadata: Optional metadata dictionary
            tags: Optional list of tags
            shared_with: Optional list of agent IDs to share with

        Returns:
            ID of the stored memory
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        memory = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            context=context,
            metadata=metadata or {},
            tags=tags or [],
            agent_id=self.agent_id,
            shared_with=shared_with or [],
        )

        return await self._store.store(memory)

    async def recall(
        self,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_relevance: float = 0.0,
        max_results: int = 10,
        include_shared: bool = True,
    ) -> List[MemorySearchResult]:
        """Search for memories.

        Args:
            query: Optional search query
            memory_type: Optional memory type filter
            tags: Optional tags filter
            min_relevance: Minimum relevance score (0-1)
            max_results: Maximum number of results
            include_shared: Whether to include shared memories

        Returns:
            List of memory search results
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        return await self._store.search(
            query=query,
            agent_id=self.agent_id,
            memory_type=memory_type,
            tags=tags,
            min_relevance=min_relevance,
            max_results=max_results,
            include_shared=include_shared,
        )

    async def forget(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if memory was deleted
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        return await self._store.delete(memory_id)

    async def update_memory(
        self, memory_id: str, updates: Dict[str, Any]
    ) -> Optional[MemoryEntry]:
        """Update a memory.

        Args:
            memory_id: ID of the memory to update
            updates: Dictionary of fields to update

        Returns:
            Updated memory if found
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        return await self._store.update(memory_id, updates)

    async def consolidate_memories(
        self, memory_ids: List[str], content: str, delete_originals: bool = True
    ) -> Optional[str]:
        """Consolidate multiple memories into a single long-term memory.

        Args:
            memory_ids: List of memory IDs to consolidate
            content: Content for the consolidated memory
            delete_originals: Whether to delete original memories

        Returns:
            ID of the consolidated memory
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        # Get original memories
        memories = []
        for memory_id in memory_ids:
            memory = await self._store.get(memory_id)
            if memory and memory.agent_id == self.agent_id:
                memories.append(memory)

        if not memories:
            return None

        # Calculate importance as average of original memories
        importance = sum(m.importance for m in memories) / len(memories)

        # Create consolidated memory
        consolidated_id = await self.remember(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            importance=importance,
            metadata={
                "consolidated_from": memory_ids,
                "original_timestamps": [m.timestamp.isoformat() for m in memories],
            },
        )

        # Delete original memories if requested
        if delete_originals:
            for memory_id in memory_ids:
                await self.forget(memory_id)

        return consolidated_id

    async def share_memories(
        self, memory_ids: List[str], target_agent_ids: List[str]
    ) -> bool:
        """Share memories with other agents.

        Args:
            memory_ids: List of memory IDs to share
            target_agent_ids: List of agent IDs to share with

        Returns:
            True if all memories were shared successfully
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        success = True
        for memory_id in memory_ids:
            result = await self._store.share_memory(
                memory_id, self.agent_id, target_agent_ids
            )
            success = success and result

        return success

    async def get_memory_stats(self) -> MemoryStats:
        """Get memory statistics.

        Returns:
            Memory statistics
        """
        if not self._store:
            raise RuntimeError("Memory manager not initialized")

        return await self._store.get_stats(self.agent_id)
