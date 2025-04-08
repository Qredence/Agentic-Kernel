"""Tests for vector search functionality using pgvector."""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from typing import AsyncGenerator, List
import asyncpg
from src.agentic_kernel.memory.types import MemoryEntry, MemoryType
from src.agentic_kernel.memory.embeddings import EmbeddingService, EmbeddingConfig
from src.agentic_kernel.memory.persistence import PostgresConfig
from src.agentic_kernel.memory.vector_store import (
    PGVectorStore,
    VectorSearchConfig,
    VectorSearchResult
)

@pytest.fixture
def vector_config():
    """Create vector search configuration."""
    return VectorSearchConfig(
        dimension=1536,  # OpenAI embedding dimension
        index_type="ivfflat",  # IVF index for approximate nearest neighbor search
        lists=100,  # Number of IVF lists, rule of thumb: sqrt(num_vectors)
        probes=10,  # Number of lists to probe during search
    )

@pytest.fixture
def postgres_config():
    """Create test database configuration."""
    return PostgresConfig(
        host=os.getenv("TEST_DB_HOST", "localhost"),
        port=int(os.getenv("TEST_DB_PORT", "5432")),
        database=os.getenv("TEST_DB_NAME", "test_memory"),
        user=os.getenv("TEST_DB_USER", "postgres"),
        password=os.getenv("TEST_DB_PASSWORD", "postgres")
    )

@pytest.fixture
def embedding_config():
    """Create test embedding configuration."""
    return EmbeddingConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        deployment_name="text-embedding-ada-002",
        cache_embeddings=True
    )

@pytest.fixture
def embedding_service(embedding_config):
    """Create embedding service."""
    return EmbeddingService(embedding_config)

@pytest.fixture
async def db_pool(postgres_config) -> AsyncGenerator[asyncpg.Pool, None]:
    """Create database connection pool."""
    pool = await asyncpg.create_pool(
        host=postgres_config.host,
        port=postgres_config.port,
        database=postgres_config.database,
        user=postgres_config.user,
        password=postgres_config.password
    )
    yield pool
    await pool.close()

@pytest.fixture
async def vector_store(db_pool, vector_config, embedding_service) -> AsyncGenerator[PGVectorStore, None]:
    """Create vector store instance."""
    store = PGVectorStore(db_pool, vector_config, embedding_service)
    await store.initialize()
    yield store
    await store.cleanup()

@pytest.mark.asyncio
async def test_vector_store_initialization(vector_store):
    """Test vector store initialization and pgvector extension."""
    async with vector_store._pool.acquire() as conn:
        # Verify pgvector extension
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            )
        """)
        assert result is True
        
        # Verify vector index
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = 'memories_embedding_idx'
                AND n.nspname = 'public'
            )
        """)
        assert result is True

@pytest.mark.asyncio
async def test_vector_similarity_search(vector_store):
    """Test vector similarity search functionality."""
    # Create test memories with different content
    memories = [
        MemoryEntry(
            id="",
            content="Python programming best practices and design patterns",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.8,
            tags=["programming", "python"]
        ),
        MemoryEntry(
            id="",
            content="Machine learning algorithms and neural networks",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.7,
            tags=["ml", "ai"]
        ),
        MemoryEntry(
            id="",
            content="Database optimization techniques and indexing strategies",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.6,
            tags=["database", "optimization"]
        )
    ]
    
    # Store memories
    memory_ids = []
    for memory in memories:
        memory_id = await vector_store.store(memory)
        memory_ids.append(memory_id)
    
    # Search for programming-related content
    results = await vector_store.search(
        query="software development and coding practices",
        limit=2,
        min_similarity=0.7
    )
    
    assert len(results) > 0
    assert any("Python" in r.memory.content for r in results)
    assert all(r.similarity >= 0.7 for r in results)
    
    # Search for ML-related content
    results = await vector_store.search(
        query="artificial intelligence and deep learning",
        limit=2,
        min_similarity=0.7
    )
    
    assert len(results) > 0
    assert any("Machine learning" in r.memory.content for r in results)
    assert all(r.similarity >= 0.7 for r in results)

@pytest.mark.asyncio
async def test_vector_search_with_filters(vector_store):
    """Test vector search with additional filters."""
    # Create memories with different types and tags
    memories = [
        MemoryEntry(
            id="",
            content="Important technical meeting notes",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.9,
            tags=["meeting", "technical"]
        ),
        MemoryEntry(
            id="",
            content="Regular team sync discussion",
            memory_type=MemoryType.SHORT_TERM,
            agent_id="agent1",
            importance=0.5,
            tags=["meeting", "team"]
        ),
        MemoryEntry(
            id="",
            content="Critical system architecture decisions",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.95,
            tags=["technical", "architecture"]
        )
    ]
    
    for memory in memories:
        await vector_store.store(memory)
    
    # Search with type filter
    results = await vector_store.search(
        query="meeting discussion",
        memory_type=MemoryType.LONG_TERM,
        min_similarity=0.7
    )
    
    assert len(results) > 0
    assert all(r.memory.memory_type == MemoryType.LONG_TERM for r in results)
    
    # Search with tag filter
    results = await vector_store.search(
        query="technical discussion",
        tags=["technical"],
        min_similarity=0.7
    )
    
    assert len(results) > 0
    assert all(any("technical" in t for t in r.memory.tags) for r in results)

@pytest.mark.asyncio
async def test_vector_search_performance(vector_store):
    """Test vector search performance with larger dataset."""
    # Create a larger set of test memories
    base_memory = {
        "id": "",
        "agent_id": "agent1",
        "memory_type": MemoryType.LONG_TERM,
        "importance": 0.7
    }
    
    # Generate varied content
    topics = ["programming", "database", "machine learning", "web development", "security"]
    contents = [
        f"{topic} concept and implementation details {i}"
        for topic in topics
        for i in range(20)  # 100 total memories
    ]
    
    memories = [
        MemoryEntry(
            **base_memory,
            content=content,
            tags=[content.split()[0]]
        )
        for content in contents
    ]
    
    # Store memories in batches
    batch_size = 20
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i + batch_size]
        await asyncio.gather(*[vector_store.store(m) for m in batch])
    
    # Measure search performance
    start_time = datetime.now()
    
    results = await vector_store.search(
        query="efficient database optimization techniques",
        limit=10,
        min_similarity=0.7
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    assert len(results) > 0
    assert duration < 1.0  # Search should complete in under 1 second
    assert all(r.similarity >= 0.7 for r in results)

@pytest.mark.asyncio
async def test_vector_index_optimization(vector_store):
    """Test vector index optimization and maintenance."""
    async with vector_store._pool.acquire() as conn:
        # Get initial index statistics
        initial_stats = await conn.fetchrow("""
            SELECT * FROM pg_indexes 
            WHERE indexname = 'memories_embedding_idx'
        """)
        
        # Add test data
        memories = [
            MemoryEntry(
                id="",
                content=f"Test memory {i}",
                memory_type=MemoryType.LONG_TERM,
                agent_id="agent1",
                importance=0.7
            )
            for i in range(50)
        ]
        
        for memory in memories:
            await vector_store.store(memory)
        
        # Verify index is being used
        query_plan = await conn.fetchval("""
            EXPLAIN (FORMAT JSON)
            SELECT * FROM memories
            ORDER BY embedding <-> $1
            LIMIT 5
        """, np.random.rand(1536).astype(np.float32).tolist())
        
        assert "Index Scan" in str(query_plan)
        
        # Test index maintenance
        await vector_store.optimize_index()
        
        # Verify index is still healthy
        final_stats = await conn.fetchrow("""
            SELECT * FROM pg_indexes 
            WHERE indexname = 'memories_embedding_idx'
        """)
        
        assert final_stats is not None 