"""Memory store for agent context storage and retrieval."""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
import logging
from .types import MemoryEntry, MemoryType, MemorySearchResult, MemoryStats
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class MemoryStore:
    """Manages agent memories with vector embeddings and sharing capabilities."""

    def __init__(self, embedding_service: EmbeddingService):
        """Initialize the memory store.

        Args:
            embedding_service: Service for generating and managing vector embeddings
        """
        self._memories: Dict[str, MemoryEntry] = {}
        self._type_index: Dict[MemoryType, Set[str]] = {t: set() for t in MemoryType}
        self._agent_index: Dict[str, Set[str]] = {}  # agent_id -> memory_ids
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> memory_ids
        self._shared_index: Dict[str, Set[str]] = {}  # agent_id -> shared_memory_ids
        self._embedding_service = embedding_service
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the memory store and cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """Stop the memory store and cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def store(self, memory: MemoryEntry) -> str:
        """Store a new memory.

        Args:
            memory: Memory entry to store

        Returns:
            ID of the stored memory
        """
        if not memory.id:
            memory.id = str(uuid.uuid4())

        # Generate embedding if not provided
        if memory.embedding is None and isinstance(memory.content, str):
            embeddings = await self._embedding_service.get_embeddings([memory.content])
            if embeddings:
                memory.embedding = embeddings[0]

        self._memories[memory.id] = memory
        self._type_index[memory.memory_type].add(memory.id)

        if memory.agent_id not in self._agent_index:
            self._agent_index[memory.agent_id] = set()
        self._agent_index[memory.agent_id].add(memory.id)

        for tag in memory.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(memory.id)

        # Update shared index
        for agent_id in memory.shared_with:
            if agent_id not in self._shared_index:
                self._shared_index[agent_id] = set()
            self._shared_index[agent_id].add(memory.id)

        return memory.id

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory entry if found, None otherwise
        """
        memory = self._memories.get(memory_id)
        if memory:
            memory.last_accessed = datetime.utcnow()
        return memory

    async def search(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_relevance: float = 0.0,
        max_results: int = 10,
        include_shared: bool = True,
    ) -> List[MemorySearchResult]:
        """Search for memories based on criteria.

        Args:
            query: Optional search query for semantic search
            agent_id: Optional agent ID to filter by
            memory_type: Optional memory type to filter by
            tags: Optional tags to filter by
            min_relevance: Minimum relevance score (0-1)
            max_results: Maximum number of results to return
            include_shared: Whether to include memories shared with the agent

        Returns:
            List of memory search results
        """
        # Get candidate memory IDs
        memory_ids = set()

        if agent_id:
            # Get agent's own memories
            memory_ids.update(self._agent_index.get(agent_id, set()))

            # Add shared memories if requested
            if include_shared:
                memory_ids.update(self._shared_index.get(agent_id, set()))

        if memory_type:
            type_ids = self._type_index.get(memory_type, set())
            memory_ids = memory_ids & type_ids if memory_ids else type_ids

        if tags:
            for tag in tags:
                tag_ids = self._tag_index.get(tag, set())
                memory_ids = memory_ids & tag_ids if memory_ids else tag_ids

        if not memory_ids:
            return []

        # Get query embedding for semantic search
        query_embedding = None
        if query:
            embeddings = await self._embedding_service.get_embeddings([query])
            if embeddings:
                query_embedding = embeddings[0]

        # Calculate relevance scores and filter results
        results: List[Tuple[MemorySearchResult, float]] = []

        for memory_id in memory_ids:
            memory = self._memories[memory_id]

            # Calculate semantic similarity if query provided
            relevance = 0.0
            if query_embedding and memory.embedding:
                relevance = self._embedding_service.calculate_similarity(
                    query_embedding, memory.embedding
                )

            if relevance >= min_relevance:
                # Calculate temporal distance score (decay over time)
                age = datetime.utcnow() - memory.timestamp
                temporal_distance = 1.0 / (
                    1.0 + age.total_seconds() / 86400
                )  # 24h decay

                # Calculate context match score (placeholder)
                context_match = 1.0

                result = MemorySearchResult(
                    entry=memory,
                    relevance=relevance,
                    context_match=context_match,
                    temporal_distance=temporal_distance,
                )

                # Use combined score for ranking
                combined_score = (
                    0.5 * relevance + 0.3 * context_match + 0.2 * temporal_distance
                )

                results.append((result, combined_score))

        # Sort by combined score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:max_results]]

    async def update(
        self, memory_id: str, updates: Dict[str, Any]
    ) -> Optional[MemoryEntry]:
        """Update an existing memory.

        Args:
            memory_id: ID of the memory to update
            updates: Dictionary of fields to update

        Returns:
            Updated memory entry if found, None otherwise
        """
        memory = self._memories.get(memory_id)
        if not memory:
            return None

        # Update fields
        for key, value in updates.items():
            if hasattr(memory, key):
                setattr(memory, key, value)

        # Update embedding if content changed
        if "content" in updates:
            embeddings = await self._embedding_service.get_embeddings([memory.content])
            if embeddings:
                memory.embedding = embeddings[0]

        memory.last_accessed = datetime.utcnow()
        return memory

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if memory was deleted, False otherwise
        """
        memory = self._memories.pop(memory_id, None)
        if not memory:
            return False

        # Remove from indexes
        self._type_index[memory.memory_type].discard(memory_id)
        self._agent_index[memory.agent_id].discard(memory_id)

        for tag in memory.tags:
            self._tag_index[tag].discard(memory_id)

        # Remove from shared index
        for agent_id in memory.shared_with:
            self._shared_index[agent_id].discard(memory_id)

        return True

    async def share_memory(
        self, memory_id: str, source_agent_id: str, target_agent_ids: List[str]
    ) -> bool:
        """Share a memory with other agents.

        Args:
            memory_id: ID of the memory to share
            source_agent_id: ID of the agent sharing the memory
            target_agent_ids: List of agent IDs to share with

        Returns:
            True if memory was shared successfully
        """
        memory = self._memories.get(memory_id)
        if not memory or memory.agent_id != source_agent_id:
            return False

        # Update shared_with list
        memory.shared_with.extend(
            agent_id
            for agent_id in target_agent_ids
            if agent_id not in memory.shared_with
        )

        # Update shared index
        for agent_id in target_agent_ids:
            if agent_id not in self._shared_index:
                self._shared_index[agent_id] = set()
            self._shared_index[agent_id].add(memory_id)

        return True

    async def get_stats(self, agent_id: str) -> MemoryStats:
        """Get memory statistics for an agent.

        Args:
            agent_id: ID of the agent

        Returns:
            Memory statistics
        """
        own_memories = self._agent_index.get(agent_id, set())
        shared_memories = self._shared_index.get(agent_id, set())

        # Count memories by type
        by_type = {t: 0 for t in MemoryType}
        for memory_id in own_memories:
            memory = self._memories[memory_id]
            by_type[memory.memory_type] += 1

        # Count memories by importance
        by_importance = {"low": 0, "medium": 0, "high": 0}
        for memory_id in own_memories:
            memory = self._memories[memory_id]
            if memory.importance < 0.33:
                by_importance["low"] += 1
            elif memory.importance < 0.66:
                by_importance["medium"] += 1
            else:
                by_importance["high"] += 1

        # Calculate total size (rough estimate)
        total_size = sum(
            len(str(memory).encode())
            for memory_id in own_memories
            if memory_id in self._memories
        )

        return MemoryStats(
            total_memories=len(own_memories),
            by_type=by_type,
            by_importance=by_importance,
            shared_memories=len(shared_memories),
            total_size=total_size,
        )

    async def _cleanup_loop(self):
        """Periodically clean up old short-term memories."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                now = datetime.utcnow()
                threshold = now - timedelta(hours=24)

                # Find old short-term memories
                to_delete = [
                    memory_id
                    for memory_id in self._type_index[MemoryType.SHORT_TERM]
                    if self._memories[memory_id].timestamp < threshold
                ]

                # Delete them
                for memory_id in to_delete:
                    await self.delete(memory_id)

                if to_delete:
                    logger.info(f"Cleaned up {len(to_delete)} old short-term memories")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(60)  # Wait before retrying
