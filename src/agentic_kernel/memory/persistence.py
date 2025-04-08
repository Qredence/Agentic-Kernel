"""Memory persistence module for PostgreSQL storage."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
import logging
from pydantic import BaseModel
import asyncpg
from .types import MemoryEntry, MemoryType, MemoryStats, MemorySearchResult
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class PostgresConfig(BaseModel):
    """Configuration for PostgreSQL connection."""

    host: str
    port: int
    database: str
    user: str
    password: str


class MigrationManager:
    """Manages database schema and migrations."""

    def __init__(self, pool: asyncpg.Pool):
        """Initialize migration manager.

        Args:
            pool: Database connection pool
        """
        self.pool = pool

    async def initialize(self):
        """Create necessary tables and indexes."""
        async with self.pool.acquire() as conn:
            # Create memories table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    last_accessed TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    agent_id TEXT NOT NULL,
                    context TEXT,
                    importance FLOAT NOT NULL,
                    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                    shared_with TEXT[] DEFAULT ARRAY[]::TEXT[],
                    source_agent_id TEXT
                )
            """
            )

            # Create embeddings table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    memory_id UUID PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
                    vector FLOAT[] NOT NULL
                )
            """
            )

            # Create indexes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_agent_id_idx ON memories(agent_id);
                CREATE INDEX IF NOT EXISTS memories_memory_type_idx ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS memories_timestamp_idx ON memories(timestamp);
                CREATE INDEX IF NOT EXISTS memories_tags_idx ON memories USING GIN(tags);
                CREATE INDEX IF NOT EXISTS memories_shared_with_idx ON memories USING GIN(shared_with);
            """
            )

    async def cleanup(self):
        """Drop all tables (for testing)."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DROP TABLE IF EXISTS embeddings CASCADE;
                DROP TABLE IF EXISTS memories CASCADE;
            """
            )


class PostgresMemoryStore:
    """Memory store implementation with PostgreSQL persistence."""

    def __init__(self, embedding_service: EmbeddingService, pool: asyncpg.Pool):
        """Initialize the persistent memory store.

        Args:
            embedding_service: Service for generating and managing embeddings
            pool: Database connection pool
        """
        self._embedding_service = embedding_service
        self._pool = pool
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
        """Store a memory in the database.

        Args:
            memory: Memory entry to store

        Returns:
            ID of the stored memory
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Generate embedding if not provided
                if memory.embedding is None and isinstance(memory.content, str):
                    embeddings = await self._embedding_service.get_embeddings(
                        [memory.content]
                    )
                    if embeddings:
                        memory.embedding = embeddings[0]

                # Store memory
                memory_id = await conn.fetchval(
                    """
                    INSERT INTO memories (
                        id, content, memory_type, timestamp, last_accessed,
                        metadata, agent_id, context, importance, tags,
                        shared_with, source_agent_id
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                    )
                    RETURNING id
                """,
                    memory.id,
                    memory.content,
                    memory.memory_type,
                    memory.timestamp,
                    memory.last_accessed,
                    json.dumps(memory.metadata),
                    memory.agent_id,
                    memory.context,
                    memory.importance,
                    memory.tags,
                    memory.shared_with,
                    memory.source_agent_id,
                )

                # Store embedding if available
                if memory.embedding:
                    await conn.execute(
                        """
                        INSERT INTO embeddings (memory_id, vector)
                        VALUES ($1, $2)
                    """,
                        memory_id,
                        memory.embedding,
                    )

                return memory_id

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory from the database.

        Args:
            memory_id: ID of the memory to retrieve

        Returns:
            Memory entry if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            # Get memory and embedding in parallel
            memory_future = conn.fetchrow(
                """
                SELECT *
                FROM memories
                WHERE id = $1
            """,
                memory_id,
            )

            embedding_future = conn.fetchval(
                """
                SELECT vector
                FROM embeddings
                WHERE memory_id = $1
            """,
                memory_id,
            )

            memory_row, embedding = await asyncio.gather(
                memory_future, embedding_future
            )

            if not memory_row:
                return None

            # Update last accessed timestamp
            await conn.execute(
                """
                UPDATE memories
                SET last_accessed = NOW()
                WHERE id = $1
            """,
                memory_id,
            )

            return MemoryEntry(
                id=memory_row["id"],
                content=memory_row["content"],
                memory_type=memory_row["memory_type"],
                timestamp=memory_row["timestamp"],
                last_accessed=memory_row["last_accessed"],
                metadata=json.loads(memory_row["metadata"]),
                agent_id=memory_row["agent_id"],
                context=memory_row["context"],
                importance=memory_row["importance"],
                tags=memory_row["tags"],
                embedding=embedding,
                shared_with=memory_row["shared_with"],
                source_agent_id=memory_row["source_agent_id"],
            )

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
        """Search for memories in the database.

        Args:
            query: Optional search query for semantic search
            agent_id: Optional agent ID to filter by
            memory_type: Optional memory type to filter by
            tags: Optional tags to filter by
            min_relevance: Minimum relevance score (0-1)
            max_results: Maximum number of results to return
            include_shared: Whether to include shared memories

        Returns:
            List of memory search results
        """
        async with self._pool.acquire() as conn:
            # Build query conditions
            conditions = []
            params = []
            param_idx = 1

            if agent_id:
                conditions.append(
                    f"(agent_id = ${param_idx} OR ($1 = ANY(shared_with) AND ${param_idx+1}))"
                )
                params.extend([agent_id, include_shared])
                param_idx += 2

            if memory_type:
                conditions.append(f"memory_type = ${param_idx}")
                params.append(memory_type)
                param_idx += 1

            if tags:
                conditions.append(f"tags && ${param_idx}::text[]")
                params.append(tags)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            # Get query embedding for semantic search
            query_embedding = None
            if query:
                embeddings = await self._embedding_service.get_embeddings([query])
                if embeddings:
                    query_embedding = embeddings[0]

            # Fetch memories and embeddings
            rows = await conn.fetch(
                f"""
                SELECT m.*, e.vector
                FROM memories m
                LEFT JOIN embeddings e ON m.id = e.memory_id
                WHERE {where_clause}
            """,
                *params,
            )

            # Calculate relevance scores and filter results
            results = []
            for row in rows:
                memory = MemoryEntry(
                    id=row["id"],
                    content=row["content"],
                    memory_type=row["memory_type"],
                    timestamp=row["timestamp"],
                    last_accessed=row["last_accessed"],
                    metadata=json.loads(row["metadata"]),
                    agent_id=row["agent_id"],
                    context=row["context"],
                    importance=row["importance"],
                    tags=row["tags"],
                    embedding=row["vector"],
                    shared_with=row["shared_with"],
                    source_agent_id=row["source_agent_id"],
                )

                # Calculate semantic similarity if query provided
                relevance = 0.0
                if query_embedding and memory.embedding:
                    relevance = self._embedding_service.calculate_similarity(
                        query_embedding, memory.embedding
                    )

                if relevance >= min_relevance:
                    # Calculate temporal distance score
                    age = datetime.utcnow() - memory.timestamp
                    temporal_distance = 1.0 / (1.0 + age.total_seconds() / 86400)

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
        """Update a memory in the database.

        Args:
            memory_id: ID of the memory to update
            updates: Dictionary of fields to update

        Returns:
            Updated memory if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Build update query
                set_clauses = []
                params = [memory_id]
                param_idx = 2

                for key, value in updates.items():
                    if key == "metadata":
                        set_clauses.append(f"{key} = ${param_idx}::jsonb")
                        params.append(json.dumps(value))
                    elif key in {"tags", "shared_with"}:
                        set_clauses.append(f"{key} = ${param_idx}::text[]")
                        params.append(value)
                    else:
                        set_clauses.append(f"{key} = ${param_idx}")
                        params.append(value)
                    param_idx += 1

                if not set_clauses:
                    return None

                # Update memory
                updated = await conn.fetchrow(
                    f"""
                    UPDATE memories
                    SET {', '.join(set_clauses)},
                        last_accessed = NOW()
                    WHERE id = $1
                    RETURNING *
                """,
                    *params,
                )

                if not updated:
                    return None

                # Update embedding if content changed
                if "content" in updates:
                    embeddings = await self._embedding_service.get_embeddings(
                        [updates["content"]]
                    )
                    if embeddings:
                        await conn.execute(
                            """
                            INSERT INTO embeddings (memory_id, vector)
                            VALUES ($1, $2)
                            ON CONFLICT (memory_id) DO UPDATE
                            SET vector = EXCLUDED.vector
                        """,
                            memory_id,
                            embeddings[0],
                        )
                        embedding = embeddings[0]
                else:
                    embedding = await conn.fetchval(
                        """
                        SELECT vector
                        FROM embeddings
                        WHERE memory_id = $1
                    """,
                        memory_id,
                    )

                return MemoryEntry(
                    id=updated["id"],
                    content=updated["content"],
                    memory_type=updated["memory_type"],
                    timestamp=updated["timestamp"],
                    last_accessed=updated["last_accessed"],
                    metadata=json.loads(updated["metadata"]),
                    agent_id=updated["agent_id"],
                    context=updated["context"],
                    importance=updated["importance"],
                    tags=updated["tags"],
                    embedding=embedding,
                    shared_with=updated["shared_with"],
                    source_agent_id=updated["source_agent_id"],
                )

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory from the database.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            True if memory was deleted
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories
                WHERE id = $1
            """,
                memory_id,
            )
            return result != "DELETE 0"

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
        async with self._pool.acquire() as conn:
            # Verify ownership
            memory = await conn.fetchrow(
                """
                SELECT shared_with
                FROM memories
                WHERE id = $1 AND agent_id = $2
            """,
                memory_id,
                source_agent_id,
            )

            if not memory:
                return False

            # Update shared_with list
            current_shared = set(memory["shared_with"])
            new_shared = current_shared.union(target_agent_ids)

            if new_shared != current_shared:
                await conn.execute(
                    """
                    UPDATE memories
                    SET shared_with = $1
                    WHERE id = $2
                """,
                    list(new_shared),
                    memory_id,
                )

            return True

    async def get_stats(self, agent_id: str) -> MemoryStats:
        """Get memory statistics from the database.

        Args:
            agent_id: ID of the agent

        Returns:
            Memory statistics
        """
        async with self._pool.acquire() as conn:
            # Get counts by type
            type_counts = await conn.fetch(
                """
                SELECT memory_type, COUNT(*) as count
                FROM memories
                WHERE agent_id = $1
                GROUP BY memory_type
            """,
                agent_id,
            )

            by_type = {t: 0 for t in MemoryType}
            for row in type_counts:
                by_type[row["memory_type"]] = row["count"]

            # Get counts by importance
            importance_counts = await conn.fetch(
                """
                SELECT
                    COUNT(*) FILTER (WHERE importance < 0.33) as low,
                    COUNT(*) FILTER (WHERE importance >= 0.33 AND importance < 0.66) as medium,
                    COUNT(*) FILTER (WHERE importance >= 0.66) as high
                FROM memories
                WHERE agent_id = $1
            """,
                agent_id,
            )

            by_importance = {
                "low": importance_counts[0]["low"],
                "medium": importance_counts[0]["medium"],
                "high": importance_counts[0]["high"],
            }

            # Get shared memory count
            shared_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM memories
                WHERE $1 = ANY(shared_with)
            """,
                agent_id,
            )

            # Get total size (rough estimate)
            total_size = await conn.fetchval(
                """
                SELECT COALESCE(SUM(
                    LENGTH(content) +
                    LENGTH(COALESCE(context, '')) +
                    LENGTH(metadata::text) +
                    array_length(tags, 1) * 20 +
                    array_length(shared_with, 1) * 20
                ), 0)
                FROM memories
                WHERE agent_id = $1
            """,
                agent_id,
            )

            return MemoryStats(
                total_memories=sum(by_type.values()),
                by_type=by_type,
                by_importance=by_importance,
                shared_memories=shared_count,
                total_size=total_size,
            )

    async def _cleanup_loop(self):
        """Periodically clean up old memories."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_memories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                await asyncio.sleep(60)

    async def _cleanup_old_memories(self):
        """Clean up old short-term memories."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM memories
                WHERE memory_type = $1
                AND timestamp < NOW() - INTERVAL '24 hours'
            """,
                MemoryType.SHORT_TERM,
            )
