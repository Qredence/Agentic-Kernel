"""Tests for memory persistence functionality."""

import pytest
import os
from datetime import datetime, timedelta
from typing import AsyncGenerator, List
import asyncio
import asyncpg
from src.agentic_kernel.memory.types import MemoryEntry, MemoryType, MemoryStats, MemorySearchResult
from src.agentic_kernel.memory.store import MemoryStore
from src.agentic_kernel.memory.embeddings import EmbeddingService, EmbeddingConfig
from src.agentic_kernel.memory.persistence import (
    PostgresMemoryStore,
    PostgresConfig,
    MigrationManager
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
        endpoint="http://test-endpoint",
        api_key="test-key",
        cache_embeddings=True
    )

@pytest.fixture
def embedding_service(embedding_config):
    """Create test embedding service."""
    return EmbeddingService(embedding_config)

@pytest.fixture
async def db_pool(postgres_config) -> AsyncGenerator[asyncpg.Pool, None]:
    """Create and manage database connection pool."""
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
async def migration_manager(db_pool):
    """Create and manage database migrations."""
    manager = MigrationManager(db_pool)
    await manager.initialize()
    yield manager
    await manager.cleanup()  # This should drop all tables

@pytest.fixture
async def memory_store(embedding_service, db_pool, migration_manager) -> AsyncGenerator[PostgresMemoryStore, None]:
    """Create test memory store with persistence."""
    store = PostgresMemoryStore(embedding_service, db_pool)
    await store.start()
    yield store
    await store.stop()

@pytest.mark.asyncio
async def test_memory_persistence_basic(memory_store):
    """Test basic memory persistence operations."""
    # Store a memory
    memory = MemoryEntry(
        id="",
        content="Test persistent memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.7,
        tags=["test", "persistent"]
    )
    
    memory_id = await memory_store.store(memory)
    assert memory_id is not None
    
    # Verify memory was stored in database
    retrieved = await memory_store.get(memory_id)
    assert retrieved is not None
    assert retrieved.content == "Test persistent memory"
    assert retrieved.memory_type == MemoryType.LONG_TERM
    assert retrieved.embedding is not None
    
    # Update the memory
    updated = await memory_store.update(memory_id, {"importance": 0.9})
    assert updated is not None
    assert updated.importance == 0.9
    
    # Delete the memory
    deleted = await memory_store.delete(memory_id)
    assert deleted is True
    
    # Verify deletion in database
    retrieved = await memory_store.get(memory_id)
    assert retrieved is None

@pytest.mark.asyncio
async def test_memory_persistence_search(memory_store):
    """Test search functionality with persistent storage."""
    # Store multiple memories
    memories = [
        MemoryEntry(
            id="",
            content=f"Persistent memory {i}",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.5 + (i * 0.1),
            tags=["test", f"tag{i}"]
        )
        for i in range(5)
    ]
    
    memory_ids = []
    for memory in memories:
        memory_id = await memory_store.store(memory)
        memory_ids.append(memory_id)
    
    # Search by content
    results = await memory_store.search(
        query="Persistent memory 0",
        agent_id="agent1"
    )
    assert len(results) > 0
    assert "Persistent memory 0" in results[0].entry.content
    
    # Search by type
    results = await memory_store.search(
        agent_id="agent1",
        memory_type=MemoryType.LONG_TERM
    )
    assert len(results) == 5
    assert all(r.entry.memory_type == MemoryType.LONG_TERM for r in results)
    
    # Search by tags
    results = await memory_store.search(
        agent_id="agent1",
        tags=["tag1"]
    )
    assert len(results) == 1
    assert "tag1" in results[0].entry.tags

@pytest.mark.asyncio
async def test_memory_persistence_sharing(memory_store):
    """Test memory sharing with persistent storage."""
    # Create and store a memory
    memory = MemoryEntry(
        id="",
        content="Shared persistent memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.8,
        tags=["test", "shared"]
    )
    
    memory_id = await memory_store.store(memory)
    
    # Share the memory
    shared = await memory_store.share_memory(
        memory_id=memory_id,
        source_agent_id="agent1",
        target_agent_ids=["agent2", "agent3"]
    )
    assert shared is True
    
    # Verify sharing persisted
    memory = await memory_store.get(memory_id)
    assert "agent2" in memory.shared_with
    assert "agent3" in memory.shared_with
    
    # Search as target agent
    results = await memory_store.search(
        agent_id="agent2",
        include_shared=True
    )
    assert any(r.entry.id == memory_id for r in results)

@pytest.mark.asyncio
async def test_memory_persistence_cleanup(memory_store):
    """Test cleanup of old memories in persistent storage."""
    # Create old and new memories
    old_memory = MemoryEntry(
        id="",
        content="Old memory",
        memory_type=MemoryType.SHORT_TERM,
        agent_id="agent1",
        importance=0.5,
        tags=["test"],
        timestamp=datetime.utcnow() - timedelta(hours=25)
    )
    
    new_memory = MemoryEntry(
        id="",
        content="New memory",
        memory_type=MemoryType.SHORT_TERM,
        agent_id="agent1",
        importance=0.5,
        tags=["test"]
    )
    
    old_id = await memory_store.store(old_memory)
    new_id = await memory_store.store(new_memory)
    
    # Run cleanup
    await memory_store._cleanup_old_memories()
    
    # Verify old memory was deleted
    old_retrieved = await memory_store.get(old_id)
    assert old_retrieved is None
    
    # Verify new memory remains
    new_retrieved = await memory_store.get(new_id)
    assert new_retrieved is not None

@pytest.mark.asyncio
async def test_memory_persistence_stats(memory_store):
    """Test memory statistics with persistent storage."""
    # Create memories with different types and importance
    memories = [
        MemoryEntry(
            id="",
            content=f"Memory {i}",
            memory_type=MemoryType.SHORT_TERM if i < 2 else MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.3 if i < 2 else (0.6 if i < 4 else 0.9),
            tags=["test"]
        )
        for i in range(6)
    ]
    
    for memory in memories:
        await memory_store.store(memory)
    
    # Get stats
    stats = await memory_store.get_stats("agent1")
    
    # Verify stats
    assert stats.total_memories == 6
    assert stats.by_type[MemoryType.SHORT_TERM] == 2
    assert stats.by_type[MemoryType.LONG_TERM] == 4
    assert stats.by_importance["low"] == 2  # importance < 0.33
    assert stats.by_importance["medium"] == 2  # 0.33 <= importance < 0.66
    assert stats.by_importance["high"] == 2  # importance >= 0.66

@pytest.mark.asyncio
async def test_migration_manager(migration_manager):
    """Test database migration functionality."""
    # Verify tables exist
    async with migration_manager.pool.acquire() as conn:
        # Check memories table
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'memories'
            )
        """)
        assert result is True
        
        # Check embeddings table
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'embeddings'
            )
        """)
        assert result is True
        
        # Check indexes
        result = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'memories'
        """)
        index_names = [r['indexname'] for r in result]
        assert 'memories_agent_id_idx' in index_names
        assert 'memories_memory_type_idx' in index_names 

@pytest.mark.asyncio
async def test_transaction_rollback(memory_store):
    """Test transaction rollback on error."""
    # Create initial memory
    memory = MemoryEntry(
        id="",
        content="Test transaction memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.7,
        tags=["test"]
    )
    
    memory_id = await memory_store.store(memory)
    
    # Attempt to update with invalid data to trigger rollback
    try:
        async with memory_store._pool.acquire() as conn:
            async with conn.transaction():
                # Update memory
                await conn.execute("""
                    UPDATE memories
                    SET importance = $1
                    WHERE id = $2
                """, 1.5, memory_id)  # Invalid importance value
                
                # This should trigger a constraint violation
                await conn.execute("""
                    UPDATE memories
                    SET memory_type = $1
                    WHERE id = $2
                """, "INVALID_TYPE", memory_id)
    except asyncpg.exceptions.CheckViolationError:
        pass
    
    # Verify memory remains unchanged
    retrieved = await memory_store.get(memory_id)
    assert retrieved.importance == 0.7
    assert retrieved.memory_type == MemoryType.LONG_TERM

@pytest.mark.asyncio
async def test_concurrent_operations(memory_store):
    """Test concurrent memory operations."""
    async def create_memory(idx: int) -> str:
        memory = MemoryEntry(
            id="",
            content=f"Concurrent memory {idx}",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=0.5,
            tags=["concurrent"]
        )
        return await memory_store.store(memory)
    
    # Create multiple memories concurrently
    tasks = [create_memory(i) for i in range(10)]
    memory_ids = await asyncio.gather(*tasks)
    
    # Verify all memories were created
    assert len(memory_ids) == 10
    
    # Verify we can retrieve all memories
    retrieval_tasks = [memory_store.get(mid) for mid in memory_ids]
    memories = await asyncio.gather(*retrieval_tasks)
    assert all(m is not None for m in memories)
    
    # Concurrent updates
    async def update_memory(memory_id: str, idx: int):
        return await memory_store.update(memory_id, {
            "content": f"Updated memory {idx}",
            "importance": 0.6
        })
    
    update_tasks = [update_memory(mid, i) for i, mid in enumerate(memory_ids)]
    updated_memories = await asyncio.gather(*update_tasks)
    assert all(m.importance == 0.6 for m in updated_memories)

@pytest.mark.asyncio
async def test_memory_sharing_edge_cases(memory_store):
    """Test edge cases in memory sharing."""
    # Create a memory
    memory = MemoryEntry(
        id="",
        content="Share test memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.7,
        tags=["test"]
    )
    memory_id = await memory_store.store(memory)
    
    # Test sharing with empty agent list
    result = await memory_store.share_memory(memory_id, "agent1", [])
    assert result is True
    
    # Test sharing with the same agent multiple times
    result = await memory_store.share_memory(memory_id, "agent1", ["agent2", "agent2"])
    assert result is True
    memory = await memory_store.get(memory_id)
    assert memory.shared_with.count("agent2") == 1
    
    # Test sharing by non-owner
    result = await memory_store.share_memory(memory_id, "agent2", ["agent3"])
    assert result is False
    
    # Test sharing after deletion
    await memory_store.delete(memory_id)
    result = await memory_store.share_memory(memory_id, "agent1", ["agent2"])
    assert result is False

@pytest.mark.asyncio
async def test_complex_search_scenarios(memory_store):
    """Test complex search scenarios."""
    # Create memories with various characteristics
    base_memory = {
        "id": "",
        "agent_id": "agent1",
        "memory_type": MemoryType.LONG_TERM,
        "importance": 0.7
    }
    
    memories = [
        MemoryEntry(**base_memory, content="Technical discussion about Python", tags=["technical", "python"]),
        MemoryEntry(**base_memory, content="Meeting notes from team sync", tags=["meeting", "team"]),
        MemoryEntry(**base_memory, content="Python code review feedback", tags=["technical", "python", "review"]),
        MemoryEntry(**base_memory, content="Team lunch discussion", tags=["team", "social"]),
    ]
    
    for memory in memories:
        await memory_store.store(memory)
    
    # Test complex tag combinations
    results = await memory_store.search(
        agent_id="agent1",
        tags=["technical", "python"],
        min_relevance=0.5
    )
    assert len(results) == 2
    
    # Test content and tag combination
    results = await memory_store.search(
        query="Python",
        agent_id="agent1",
        tags=["technical"],
        min_relevance=0.5
    )
    assert len(results) == 2
    
    # Test exclusion patterns
    results = await memory_store.search(
        agent_id="agent1",
        tags=["team"],
        query="technical",
        min_relevance=0.5
    )
    assert len(results) == 0

@pytest.mark.asyncio
async def test_performance_under_load(memory_store):
    """Test memory store performance under load."""
    # Create many memories
    base_memory = {
        "id": "",
        "agent_id": "agent1",
        "memory_type": MemoryType.LONG_TERM,
        "importance": 0.7
    }
    
    async def create_batch(start_idx: int, count: int):
        for i in range(start_idx, start_idx + count):
            memory = MemoryEntry(
                **base_memory,
                content=f"Performance test memory {i}",
                tags=[f"tag{i % 5}"]
            )
            await memory_store.store(memory)
    
    # Create 100 memories in parallel batches
    batch_size = 20
    tasks = [
        create_batch(i * batch_size, batch_size)
        for i in range(5)
    ]
    await asyncio.gather(*tasks)
    
    # Perform concurrent searches
    async def search_memories(query: str):
        return await memory_store.search(
            query=query,
            agent_id="agent1",
            max_results=10
        )
    
    search_tasks = [
        search_memories(f"memory {i}")
        for i in range(10)
    ]
    results = await asyncio.gather(*search_tasks)
    assert all(len(r) > 0 for r in results)

@pytest.mark.asyncio
async def test_error_handling_and_recovery(memory_store):
    """Test error handling and recovery scenarios."""
    # Test invalid memory type
    with pytest.raises(ValueError):
        memory = MemoryEntry(
            id="",
            content="Invalid memory",
            memory_type="INVALID_TYPE",  # type: ignore
            agent_id="agent1",
            importance=0.7
        )
        await memory_store.store(memory)
    
    # Test invalid importance value
    with pytest.raises(ValueError):
        memory = MemoryEntry(
            id="",
            content="Invalid memory",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent1",
            importance=1.5
        )
        await memory_store.store(memory)
    
    # Test recovery after failed operation
    valid_memory = MemoryEntry(
        id="",
        content="Valid memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.7
    )
    memory_id = await memory_store.store(valid_memory)
    assert memory_id is not None
    
    # Test handling of concurrent deletion
    async def concurrent_operations():
        tasks = [
            memory_store.delete(memory_id),
            memory_store.update(memory_id, {"importance": 0.8})
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    results = await concurrent_operations()
    assert any(isinstance(r, Exception) for r in results)

@pytest.mark.asyncio
async def test_cleanup_with_shared_memories(memory_store):
    """Test cleanup behavior with shared memories."""
    # Create memories with different ages
    old_shared = MemoryEntry(
        id="",
        content="Old shared memory",
        memory_type=MemoryType.SHORT_TERM,
        agent_id="agent1",
        importance=0.5,
        timestamp=datetime.utcnow() - timedelta(hours=25),
        shared_with=["agent2"]
    )
    
    new_shared = MemoryEntry(
        id="",
        content="New shared memory",
        memory_type=MemoryType.SHORT_TERM,
        agent_id="agent1",
        importance=0.5,
        shared_with=["agent2"]
    )
    
    old_id = await memory_store.store(old_shared)
    new_id = await memory_store.store(new_shared)
    
    # Run cleanup
    await memory_store._cleanup_old_memories()
    
    # Verify old memory was deleted despite being shared
    old_retrieved = await memory_store.get(old_id)
    assert old_retrieved is None
    
    # Verify new memory remains
    new_retrieved = await memory_store.get(new_id)
    assert new_retrieved is not None
    assert "agent2" in new_retrieved.shared_with 