"""Tests for the memory module."""

import pytest
from datetime import datetime, timedelta
from src.agentic_kernel.memory.types import MemoryEntry, MemoryType, MemoryStats
from src.agentic_kernel.memory.store import MemoryStore
from src.agentic_kernel.memory.manager import MemoryManager
from src.agentic_kernel.memory.embeddings import EmbeddingService, EmbeddingConfig

@pytest.fixture
def embedding_config():
    """Create a test embedding configuration."""
    return EmbeddingConfig(
        endpoint="http://test-endpoint",
        api_key="test-key",
        cache_embeddings=True
    )

@pytest.fixture
def embedding_service(embedding_config):
    """Create a test embedding service."""
    return EmbeddingService(embedding_config)

@pytest.fixture
async def memory_store(embedding_service):
    """Create a test memory store."""
    store = MemoryStore(embedding_service)
    await store.start()
    yield store
    await store.stop()

@pytest.fixture
async def memory_manager(memory_store):
    """Create a test memory manager."""
    manager = MemoryManager(store=memory_store)
    await manager.start()
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_memory_store_basic_operations(memory_store):
    """Test basic memory store operations."""
    # Store a memory
    memory = MemoryEntry(
        id="",
        content="Test memory content",
        memory_type=MemoryType.SHORT_TERM,
        agent_id="agent1",
        importance=0.5,
        tags=["test"]
    )
    
    memory_id = await memory_store.store(memory)
    assert memory_id is not None
    
    # Retrieve the memory
    retrieved = await memory_store.get(memory_id)
    assert retrieved is not None
    assert retrieved.content == "Test memory content"
    assert retrieved.memory_type == MemoryType.SHORT_TERM
    assert retrieved.agent_id == "agent1"
    assert retrieved.embedding is not None  # Should have generated embedding
    
    # Update the memory
    updated = await memory_store.update(memory_id, {"importance": 0.8})
    assert updated is not None
    assert updated.importance == 0.8
    
    # Delete the memory
    deleted = await memory_store.delete(memory_id)
    assert deleted is True
    
    # Verify deletion
    retrieved = await memory_store.get(memory_id)
    assert retrieved is None

@pytest.mark.asyncio
async def test_memory_store_search(memory_store):
    """Test memory store search functionality."""
    # Store test memories
    memories = [
        MemoryEntry(
            id="",
            content=f"Memory {i}",
            memory_type=MemoryType.SHORT_TERM if i % 2 == 0 else MemoryType.LONG_TERM,
            agent_id="agent1" if i < 3 else "agent2",
            importance=0.5,
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
        query="Memory 0",
        agent_id="agent1"
    )
    assert len(results) > 0
    assert results[0].entry.content == "Memory 0"
    
    # Search by type
    results = await memory_store.search(
        agent_id="agent1",
        memory_type=MemoryType.SHORT_TERM
    )
    assert all(r.entry.memory_type == MemoryType.SHORT_TERM for r in results)
    
    # Search by tags
    results = await memory_store.search(
        agent_id="agent1",
        tags=["tag1"]
    )
    assert all("tag1" in r.entry.tags for r in results)

@pytest.mark.asyncio
async def test_memory_sharing(memory_store):
    """Test memory sharing functionality."""
    # Create a memory
    memory = MemoryEntry(
        id="",
        content="Shared memory",
        memory_type=MemoryType.LONG_TERM,
        agent_id="agent1",
        importance=0.7,
        tags=["shared"]
    )
    
    memory_id = await memory_store.store(memory)
    
    # Share with other agents
    shared = await memory_store.share_memory(
        memory_id=memory_id,
        source_agent_id="agent1",
        target_agent_ids=["agent2", "agent3"]
    )
    assert shared is True
    
    # Verify sharing
    memory = await memory_store.get(memory_id)
    assert "agent2" in memory.shared_with
    assert "agent3" in memory.shared_with
    
    # Search as target agent
    results = await memory_store.search(
        agent_id="agent2",
        include_shared=True
    )
    assert any(r.entry.id == memory_id for r in results)
    
    # Search without shared memories
    results = await memory_store.search(
        agent_id="agent2",
        include_shared=False
    )
    assert not any(r.entry.id == memory_id for r in results)

@pytest.mark.asyncio
async def test_memory_manager_operations(memory_manager):
    """Test memory manager operations."""
    # Store a memory
    memory_id = await memory_manager.remember(
        agent_id="agent1",
        content="Test memory",
        memory_type=MemoryType.SHORT_TERM,
        importance=0.6,
        tags=["test"],
        shared_with=["agent2"]
    )
    assert memory_id is not None
    
    # Search for the memory
    results = await memory_manager.recall(
        agent_id="agent1",
        query="Test memory"
    )
    assert len(results) > 0
    assert results[0].entry.content == "Test memory"
    
    # Update the memory
    updated = await memory_manager.update_memory(
        agent_id="agent1",
        memory_id=memory_id,
        updates={"importance": 0.8}
    )
    assert updated is not None
    assert updated.importance == 0.8
    
    # Share with more agents
    shared = await memory_manager.share_memories(
        source_agent_id="agent1",
        target_agent_ids=["agent3"],
        memory_ids=[memory_id]
    )
    assert shared is True
    
    # Get memory stats
    stats = await memory_manager.get_memory_stats("agent1")
    assert stats.total_memories == 1
    assert stats.by_type[MemoryType.SHORT_TERM] == 1
    assert stats.shared_memories == 1

@pytest.mark.asyncio
async def test_memory_consolidation(memory_manager):
    """Test memory consolidation functionality."""
    # Create multiple short-term memories
    memory_ids = []
    for i in range(3):
        memory_id = await memory_manager.remember(
            agent_id="agent1",
            content=f"Memory {i}",
            memory_type=MemoryType.SHORT_TERM,
            importance=0.5,
            tags=[f"tag{i}"]
        )
        memory_ids.append(memory_id)
    
    # Consolidate memories
    consolidated_id = await memory_manager.consolidate_memories(
        agent_id="agent1",
        memory_ids=memory_ids,
        summary="Consolidated memory",
        importance=0.8
    )
    assert consolidated_id is not None
    
    # Verify consolidation
    consolidated = await memory_manager._store.get(consolidated_id)
    assert consolidated is not None
    assert consolidated.memory_type == MemoryType.LONG_TERM
    assert consolidated.importance == 0.8
    
    # Verify original memories are deleted
    for memory_id in memory_ids:
        memory = await memory_manager._store.get(memory_id)
        assert memory is None

@pytest.mark.asyncio
async def test_embedding_service(embedding_service):
    """Test embedding service functionality."""
    # Get embeddings
    texts = ["Test text 1", "Test text 2"]
    embeddings = await embedding_service.get_embeddings(texts)
    
    assert len(embeddings) == 2
    assert all(len(embedding) == 1536 for embedding in embeddings)  # text-embedding-3-small dimension
    
    # Test similarity calculation
    similarity = embedding_service.calculate_similarity(embeddings[0], embeddings[1])
    assert 0 <= similarity <= 1
    
    # Test caching
    cached_embeddings = await embedding_service.get_embeddings(texts)
    assert embeddings == cached_embeddings
    
    # Clear cache
    embedding_service.clear_cache()
    assert len(embedding_service._cache) == 0 