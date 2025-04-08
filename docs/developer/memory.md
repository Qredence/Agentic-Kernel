# Memory System Developer Guide

## Overview

The Agentic Kernel memory system provides both short-term (working) and long-term memory capabilities for agents. This guide covers the memory system architecture, implementation details, and best practices for development.

## Core Components

### Memory Types

1. **Working Memory**
   - Short-term task context
   - Temporary data storage
   - Task-specific information

2. **Long-term Memory**
   - Persistent knowledge storage
   - Historical information
   - Learned patterns and rules

### Memory Interface

The base memory interface in `src/agentic_kernel/memory/base.py`:

```python
class BaseMemory:
    """Base class for memory implementations."""
    
    async def store(self, key: str, value: Any, context: Optional[Dict] = None) -> None:
        """Store a value in memory."""
        raise NotImplementedError
    
    async def retrieve(self, key: str, context: Optional[Dict] = None) -> Optional[Any]:
        """Retrieve a value from memory."""
        raise NotImplementedError
    
    async def search(self, query: str, context: Optional[Dict] = None) -> List[Any]:
        """Search memory for relevant information."""
        raise NotImplementedError
    
    async def forget(self, key: str) -> None:
        """Remove information from memory."""
        raise NotImplementedError
```

## Implementation Guide

### Working Memory

Example working memory implementation:

```python
from agentic_kernel.memory.base import BaseMemory
from typing import Dict, Any, Optional, List
import asyncio

class WorkingMemory(BaseMemory):
    def __init__(self, ttl: int = 3600):
        self._storage = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()
    
    async def store(self, key: str, value: Any, context: Optional[Dict] = None) -> None:
        async with self._lock:
            self._storage[key] = {
                'value': value,
                'context': context,
                'timestamp': time.time()
            }
    
    async def retrieve(self, key: str, context: Optional[Dict] = None) -> Optional[Any]:
        async with self._lock:
            if key not in self._storage:
                return None
                
            entry = self._storage[key]
            if time.time() - entry['timestamp'] > self._ttl:
                del self._storage[key]
                return None
                
            return entry['value']
    
    async def search(self, query: str, context: Optional[Dict] = None) -> List[Any]:
        results = []
        async with self._lock:
            for key, entry in self._storage.items():
                if self._matches_query(query, entry, context):
                    results.append(entry['value'])
        return results
    
    async def forget(self, key: str) -> None:
        async with self._lock:
            self._storage.pop(key, None)
```

### Long-term Memory

Example long-term memory implementation:

```python
from agentic_kernel.memory.base import BaseMemory
from typing import Dict, Any, Optional, List
import sqlite3
import json

class LongTermMemory(BaseMemory):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    context TEXT,
                    timestamp REAL
                )
            """)
    
    async def store(self, key: str, value: Any, context: Optional[Dict] = None) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory VALUES (?, ?, ?, ?)",
                (key, json.dumps(value), json.dumps(context), time.time())
            )
    
    async def retrieve(self, key: str, context: Optional[Dict] = None) -> Optional[Any]:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM memory WHERE key = ?",
                (key,)
            )
            if row := cursor.fetchone():
                return json.loads(row[0])
        return None
```

## Memory Context

Memory contexts help organize and retrieve information:

```python
class MemoryContext:
    def __init__(self, task_id: str, agent_id: str):
        self.task_id = task_id
        self.agent_id = agent_id
        self.metadata = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'metadata': self.metadata
        }
```

## Memory Management

### Garbage Collection

Implement memory cleanup:

```python
class MemoryManager:
    def __init__(self, working_memory: WorkingMemory, long_term_memory: LongTermMemory):
        self._working_memory = working_memory
        self._long_term_memory = long_term_memory
    
    async def cleanup_working_memory(self) -> None:
        """Remove expired entries from working memory."""
        current_time = time.time()
        async with self._working_memory._lock:
            expired = [
                key for key, entry in self._working_memory._storage.items()
                if current_time - entry['timestamp'] > self._working_memory._ttl
            ]
            for key in expired:
                await self._working_memory.forget(key)
```

### Memory Indexing

Implement efficient retrieval:

```python
class MemoryIndex:
    def __init__(self):
        self._index = {}
    
    def add_entry(self, key: str, value: Any, metadata: Dict[str, Any]) -> None:
        """Index a memory entry for faster retrieval."""
        tokens = self._tokenize(str(value))
        for token in tokens:
            if token not in self._index:
                self._index[token] = set()
            self._index[token].add(key)
    
    def search(self, query: str) -> Set[str]:
        """Search the index for relevant entries."""
        tokens = self._tokenize(query)
        if not tokens:
            return set()
            
        results = self._index.get(tokens[0], set())
        for token in tokens[1:]:
            results &= self._index.get(token, set())
        return results
```

## Best Practices

1. **Concurrency**
   - Use proper locking mechanisms
   - Handle concurrent access
   - Implement atomic operations

2. **Performance**
   - Implement efficient indexing
   - Use appropriate data structures
   - Cache frequently accessed data

3. **Data Integrity**
   - Validate input data
   - Handle serialization properly
   - Implement error recovery

4. **Memory Limits**
   - Set appropriate size limits
   - Implement cleanup policies
   - Monitor memory usage

5. **Context Management**
   - Use meaningful contexts
   - Implement context inheritance
   - Clean up unused contexts

## Testing

Example memory system tests:

```python
import pytest
from agentic_kernel.memory import WorkingMemory, LongTermMemory

@pytest.fixture
def working_memory():
    return WorkingMemory(ttl=60)

@pytest.fixture
def long_term_memory():
    return LongTermMemory(":memory:")

@pytest.mark.asyncio
async def test_working_memory_store_retrieve(working_memory):
    await working_memory.store("test_key", "test_value")
    value = await working_memory.retrieve("test_key")
    assert value == "test_value"

@pytest.mark.asyncio
async def test_working_memory_expiration(working_memory):
    working_memory._ttl = 0  # Immediate expiration
    await working_memory.store("test_key", "test_value")
    value = await working_memory.retrieve("test_key")
    assert value is None
```

## Common Patterns

### Memory Hierarchies

```python
class HierarchicalMemory(BaseMemory):
    def __init__(self, layers: List[BaseMemory]):
        self._layers = layers
    
    async def retrieve(self, key: str, context: Optional[Dict] = None) -> Optional[Any]:
        for layer in self._layers:
            if value := await layer.retrieve(key, context):
                return value
        return None
```

### Memory Policies

```python
class MemoryPolicy:
    def __init__(self, max_size: int, cleanup_threshold: float = 0.9):
        self.max_size = max_size
        self.cleanup_threshold = cleanup_threshold
    
    def should_cleanup(self, current_size: int) -> bool:
        return current_size >= self.max_size * self.cleanup_threshold
```

## Troubleshooting

Common issues and solutions:

1. **Memory Leaks**
   - Implement proper cleanup
   - Monitor memory usage
   - Use weak references

2. **Performance Issues**
   - Optimize indexing
   - Implement caching
   - Profile memory operations

3. **Concurrency Problems**
   - Use proper locking
   - Implement atomic operations
   - Handle deadlocks
``` 