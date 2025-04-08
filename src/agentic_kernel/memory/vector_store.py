"""Vector store implementation using pgvector."""

import asyncio
import numpy as np
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncpg
from .types import MemoryEntry, MemoryType
from .embeddings import EmbeddingService


@dataclass
class VectorSearchConfig:
    """Configuration for vector search using pgvector."""

    dimension: int = 1536  # OpenAI embedding dimension
    index_type: str = "ivfflat"  # IVF index for approximate nearest neighbor search
    lists: int = 100  # Number of IVF lists, rule of thumb: sqrt(num_vectors)
    probes: int = 10  # Number of lists to probe during search


@dataclass
class VectorSearchResult:
    """Result from a vector similarity search."""

    memory: MemoryEntry
    similarity: float


class PGVectorStore:
    """Vector store implementation using PostgreSQL with pgvector extension."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        config: VectorSearchConfig,
        embedding_service: EmbeddingService,
    ):
        """Initialize the vector store.

        Args:
            pool: Database connection pool
            config: Vector search configuration
            embedding_service: Service for generating embeddings
        """
        self._pool = pool
        self._config = config
        self._embedding_service = embedding_service

    async def initialize(self):
        """Initialize the vector store, creating necessary extensions and tables."""
        async with self._pool.acquire() as conn:
            # Create vector extension if not exists
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create memories table with vector support
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    importance FLOAT NOT NULL CHECK (importance >= 0 AND importance <= 1),
                    tags TEXT[] NOT NULL DEFAULT '{}',
                    shared_with TEXT[] NOT NULL DEFAULT '{}',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    embedding vector({dimension})
                )
            """.format(
                    dimension=self._config.dimension
                )
            )

            # Create indexes
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_agent_id_idx ON memories(agent_id);
                CREATE INDEX IF NOT EXISTS memories_memory_type_idx ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS memories_timestamp_idx ON memories(timestamp);
            """
            )

            # Create vector index
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories 
                USING ivfflat (embedding vector_l2_ops)
                WITH (lists = {lists})
            """.format(
                    lists=self._config.lists
                )
            )

            # Set number of probes for search
            await conn.execute(
                """
                SET ivfflat.probes = {probes}
            """.format(
                    probes=self._config.probes
                )
            )

    async def cleanup(self):
        """Clean up resources."""
        # Nothing to clean up for now
        pass

    async def store(self, memory: MemoryEntry) -> str:
        """Store a memory with its vector embedding.

        Args:
            memory: Memory entry to store

        Returns:
            str: ID of stored memory
        """
        # Generate embedding if not provided
        if not memory.embedding:
            memory.embedding = await self._embedding_service.get_embeddings(
                [memory.content]
            )
            memory.embedding = memory.embedding[0]  # Get first embedding

        async with self._pool.acquire() as conn:
            memory_id = await conn.fetchval(
                """
                INSERT INTO memories (
                    content, memory_type, agent_id, importance,
                    tags, shared_with, embedding
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id::text
            """,
                memory.content,
                memory.memory_type,
                memory.agent_id,
                memory.importance,
                memory.tags,
                memory.shared_with or [],
                memory.embedding,
            )

            return memory_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7,
        memory_type: Optional[MemoryType] = None,
        agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar memories using vector similarity.

        Args:
            query: Search query
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            memory_type: Filter by memory type
            agent_id: Filter by agent ID
            tags: Filter by tags

        Returns:
            List of search results with similarity scores
        """
        # Generate query embedding
        query_embedding = await self._embedding_service.get_embeddings([query])
        query_embedding = query_embedding[0]

        # Build query conditions
        conditions = []
        params: List[Any] = [query_embedding, min_similarity]
        param_idx = 3

        if memory_type:
            conditions.append(f"memory_type = ${param_idx}")
            params.append(memory_type)
            param_idx += 1

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if tags:
            conditions.append(f"tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        where_clause = " AND ".join(conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause

        # Execute search query
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT 
                    id,
                    content,
                    memory_type,
                    agent_id,
                    importance,
                    tags,
                    shared_with,
                    timestamp,
                    embedding,
                    1 - (embedding <-> $1) as similarity
                FROM memories
                {where_clause}
                AND 1 - (embedding <-> $1) >= $2
                ORDER BY similarity DESC
                LIMIT {limit}
            """,
                *params,
            )

            results = []
            for row in rows:
                memory = MemoryEntry(
                    id=str(row["id"]),
                    content=row["content"],
                    memory_type=row["memory_type"],
                    agent_id=row["agent_id"],
                    importance=row["importance"],
                    tags=row["tags"],
                    shared_with=row["shared_with"],
                    timestamp=row["timestamp"],
                    embedding=row["embedding"],
                )
                results.append(
                    VectorSearchResult(memory=memory, similarity=row["similarity"])
                )

            return results

    async def optimize_index(self):
        """Optimize the vector index for better search performance."""
        async with self._pool.acquire() as conn:
            # Analyze table statistics
            await conn.execute("ANALYZE memories")

            # Reindex to optimize
            await conn.execute(
                """
                REINDEX INDEX memories_embedding_idx;
                VACUUM ANALYZE memories;
            """
            )

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID.

        Args:
            memory_id: ID of memory to delete

        Returns:
            bool: True if memory was deleted
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories
                WHERE id = $1::uuid
            """,
                memory_id,
            )
            return result == "DELETE 1"

    async def update(
        self, memory_id: str, updates: Dict[str, Any]
    ) -> Optional[MemoryEntry]:
        """Update a memory by ID.

        Args:
            memory_id: ID of memory to update
            updates: Dictionary of fields to update

        Returns:
            Updated memory entry or None if not found
        """
        # Generate new embedding if content is updated
        if "content" in updates:
            embedding = await self._embedding_service.get_embeddings(
                [updates["content"]]
            )
            updates["embedding"] = embedding[0]

        # Build update query
        set_clauses = []
        params = [memory_id]
        param_idx = 2

        for key, value in updates.items():
            if key in [
                "content",
                "memory_type",
                "agent_id",
                "importance",
                "tags",
                "shared_with",
                "embedding",
            ]:
                set_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not set_clauses:
            return None

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE memories
                SET {', '.join(set_clauses)}
                WHERE id = $1::uuid
                RETURNING *
            """,
                *params,
            )

            if not row:
                return None

            return MemoryEntry(
                id=str(row["id"]),
                content=row["content"],
                memory_type=row["memory_type"],
                agent_id=row["agent_id"],
                importance=row["importance"],
                tags=row["tags"],
                shared_with=row["shared_with"],
                timestamp=row["timestamp"],
                embedding=row["embedding"],
            )
