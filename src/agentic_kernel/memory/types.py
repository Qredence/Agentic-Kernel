"""Memory types and data structures."""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """Types of memory storage."""

    SHORT_TERM = "short_term"  # Temporary, session-based memory
    LONG_TERM = "long_term"  # Persistent memory across sessions
    WORKING = "working"  # Active processing memory
    EPISODIC = "episodic"  # Event-based memories with temporal context
    COLLABORATIVE = "collaborative"  # Shared workspace for collaborative reasoning


class MemoryEntry(BaseModel):
    """A single memory entry in the store.

    Attributes:
        id: Unique identifier for the memory
        content: The actual memory content
        memory_type: Type of memory (short-term, long-term, etc.)
        timestamp: When the memory was created
        last_accessed: When the memory was last accessed
        metadata: Additional information about the memory
        agent_id: ID of the agent that created the memory
        context: Related context for the memory
        importance: Importance score (0-1)
        tags: List of tags for categorization
        embedding: Vector embedding for semantic search
        shared_with: List of agent IDs this memory is shared with
        source_agent_id: Original agent if memory is shared
    """

    id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    context: Optional[str] = None
    importance: float = 0.5
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    shared_with: List[str] = Field(default_factory=list)
    source_agent_id: Optional[str] = None

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class MemorySearchResult(BaseModel):
    """Result of a memory search operation.

    Attributes:
        entry: The found memory entry
        relevance: How relevant the memory is to the search (0-1)
        context_match: How well the context matches (0-1)
        temporal_distance: Time distance from current time
    """

    entry: MemoryEntry
    relevance: float  # Semantic similarity score
    context_match: float  # Context relevance score
    temporal_distance: float  # Time-based relevance score

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True


class MemoryStats(BaseModel):
    """Statistics about an agent's memories."""

    total_memories: int
    by_type: Dict[MemoryType, int]
    by_importance: Dict[str, int]  # low/medium/high
    shared_memories: int
    total_size: int  # in bytes
