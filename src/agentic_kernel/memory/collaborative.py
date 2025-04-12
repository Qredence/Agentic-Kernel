"""Collaborative memory system for agent reasoning.

This module implements a shared memory system for collaborative agent reasoning,
allowing multiple agents to work together on complex tasks by sharing a common
memory workspace.

Key features:
1. Collaborative workspaces for multi-agent reasoning
2. Synchronized memory access and updates
3. Conflict detection and resolution
4. Memory versioning and history
5. Access control and permissions
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from .manager import MemoryManager
from .types import MemoryEntry, MemorySearchResult, MemoryType

# COLLABORATIVE type is defined in types.py

logger = logging.getLogger(__name__)


class CollaborationRole(str, Enum):
    """Roles for agents in a collaborative workspace."""

    OWNER = "owner"  # Can manage workspace and permissions
    CONTRIBUTOR = "contributor"  # Can read and write to workspace
    READER = "reader"  # Can only read from workspace


class CollaborativeMemoryEntry(MemoryEntry):
    """A memory entry in a collaborative workspace.

    Extends the base MemoryEntry with additional fields for collaboration.

    Attributes:
        workspace_id: ID of the workspace this memory belongs to
        version: Version number of this memory entry
        created_by: ID of the agent that created this entry
        modified_by: ID of the agent that last modified this entry
        locked_by: ID of the agent that has locked this entry for editing
        lock_expiry: When the lock expires
        comments: Comments from agents about this memory
    """

    workspace_id: str
    version: int = 1
    created_by: str
    modified_by: Optional[str] = None
    locked_by: Optional[str] = None
    lock_expiry: Optional[datetime] = None
    comments: List[Dict[str, Any]] = Field(default_factory=list)


class CollaborativeWorkspace(BaseModel):
    """A shared workspace for collaborative agent reasoning.

    Attributes:
        id: Unique identifier for the workspace
        name: Name of the workspace
        description: Description of the workspace
        created_at: When the workspace was created
        created_by: ID of the agent that created the workspace
        members: Dict mapping agent IDs to their roles
        tags: List of tags for categorization
        status: Current status of the workspace
        metadata: Additional information about the workspace
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    members: Dict[str, CollaborationRole] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CollaborativeMemoryManager:
    """Manager for collaborative memory workspaces.

    This class provides methods for creating and managing collaborative
    workspaces, as well as reading and writing to shared memories.

    Attributes:
        memory_manager: The underlying memory manager
        workspaces: Dict mapping workspace IDs to workspace objects
        locks: Dict tracking memory locks
    """

    def __init__(self, memory_manager: MemoryManager):
        """Initialize the collaborative memory manager.

        Args:
            memory_manager: The underlying memory manager
        """
        self.memory_manager = memory_manager
        self.workspaces: Dict[str, CollaborativeWorkspace] = {}
        self.locks: Dict[str, Dict[str, Any]] = {}
        self._lock_cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the collaborative memory manager."""
        self._lock_cleanup_task = asyncio.create_task(self._lock_cleanup_loop())
        logger.info("Collaborative memory manager started")

    async def stop(self) -> None:
        """Stop the collaborative memory manager."""
        if self._lock_cleanup_task:
            self._lock_cleanup_task.cancel()
            try:
                await self._lock_cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Collaborative memory manager stopped")

    async def create_workspace(
        self, name: str, description: str, created_by: str, tags: Optional[List[str]] = None
    ) -> CollaborativeWorkspace:
        """Create a new collaborative workspace.

        Args:
            name: Name of the workspace
            description: Description of the workspace
            created_by: ID of the agent creating the workspace
            tags: Optional tags for the workspace

        Returns:
            The created workspace
        """
        workspace = CollaborativeWorkspace(
            name=name,
            description=description,
            created_by=created_by,
            tags=tags or [],
            members={created_by: CollaborationRole.OWNER},
        )
        self.workspaces[workspace.id] = workspace
        logger.info(f"Created collaborative workspace {workspace.id} ({name})")
        return workspace

    async def get_workspace(
        self, workspace_id: str
    ) -> Optional[CollaborativeWorkspace]:
        """Get a workspace by ID.

        Args:
            workspace_id: ID of the workspace to get

        Returns:
            The workspace if found, None otherwise
        """
        return self.workspaces.get(workspace_id)

    async def add_member(
        self, workspace_id: str, agent_id: str, role: CollaborationRole
    ) -> bool:
        """Add a member to a workspace.

        Args:
            workspace_id: ID of the workspace
            agent_id: ID of the agent to add
            role: Role for the agent

        Returns:
            True if the member was added successfully
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return False

        workspace.members[agent_id] = role
        logger.info(
            f"Added agent {agent_id} to workspace {workspace_id} with role {role}"
        )
        return True

    async def remove_member(self, workspace_id: str, agent_id: str) -> bool:
        """Remove a member from a workspace.

        Args:
            workspace_id: ID of the workspace
            agent_id: ID of the agent to remove

        Returns:
            True if the member was removed successfully
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return False

        del workspace.members[agent_id]
        logger.info(f"Removed agent {agent_id} from workspace {workspace_id}")
        return True

    async def store_memory(
        self,
        workspace_id: str,
        agent_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a memory in a collaborative workspace.

        Args:
            workspace_id: ID of the workspace
            agent_id: ID of the agent storing the memory
            content: Content of the memory
            tags: Optional tags for the memory
            importance: Importance score (0-1)
            metadata: Additional metadata

        Returns:
            ID of the stored memory if successful, None otherwise
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return None

        # Check if agent has permission to write
        role = workspace.members[agent_id]
        if role not in [CollaborationRole.OWNER, CollaborationRole.CONTRIBUTOR]:
            logger.warning(
                f"Agent {agent_id} does not have permission to write to workspace {workspace_id}"
            )
            return None

        # Create collaborative memory entry
        memory_id = await self.memory_manager.remember(
            content=content,
            memory_type=MemoryType.COLLABORATIVE,
            tags=tags or [],
            importance=importance,
            metadata=metadata or {},
        )

        # Add workspace-specific metadata
        await self.memory_manager.update_memory(
            memory_id,
            {
                "workspace_id": workspace_id,
                "created_by": agent_id,
                "version": 1,
            },
        )

        logger.info(
            f"Stored collaborative memory {memory_id} in workspace {workspace_id}"
        )
        return memory_id

    async def get_memory(
        self, workspace_id: str, memory_id: str, agent_id: str
    ) -> Optional[MemoryEntry]:
        """Get a memory from a collaborative workspace.

        Args:
            workspace_id: ID of the workspace
            memory_id: ID of the memory to get
            agent_id: ID of the agent requesting the memory

        Returns:
            The memory entry if found and accessible, None otherwise
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return None

        # Search for the memory by ID
        results = await self.memory_manager.recall(memory_id)
        if not results:
            return None

        # Find the memory with the matching ID
        memory_result = next((r for r in results if r.entry.id == memory_id), None)
        if not memory_result:
            return None

        memory = memory_result.entry

        # Check if memory belongs to this workspace
        if memory.metadata.get("workspace_id") != workspace_id:
            return None

        # Update last accessed time
        await self.memory_manager.update_memory(
            memory_id, {"last_accessed": datetime.utcnow()}
        )

        return memory

    async def update_memory(
        self,
        workspace_id: str,
        memory_id: str,
        agent_id: str,
        updates: Dict[str, Any],
    ) -> Optional[MemoryEntry]:
        """Update a memory in a collaborative workspace.

        Args:
            workspace_id: ID of the workspace
            memory_id: ID of the memory to update
            agent_id: ID of the agent updating the memory
            updates: Updates to apply to the memory

        Returns:
            The updated memory if successful, None otherwise
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return None

        # Check if agent has permission to write
        role = workspace.members[agent_id]
        if role not in [CollaborationRole.OWNER, CollaborationRole.CONTRIBUTOR]:
            logger.warning(
                f"Agent {agent_id} does not have permission to update memory {memory_id}"
            )
            return None

        # Check if memory is locked by another agent
        lock = self.locks.get(memory_id)
        if lock and lock["agent_id"] != agent_id and lock["expiry"] > datetime.utcnow():
            logger.warning(f"Memory {memory_id} is locked by agent {lock['agent_id']}")
            return None

        # Search for the memory by ID
        results = await self.memory_manager.recall(memory_id)
        if not results:
            return None

        # Find the memory with the matching ID
        memory_result = next((r for r in results if r.entry.id == memory_id), None)
        if not memory_result:
            return None

        memory = memory_result.entry

        # Check if memory belongs to this workspace
        if memory.metadata.get("workspace_id") != workspace_id:
            return None

        # Update version and modified_by
        updates["version"] = memory.metadata.get("version", 1) + 1
        updates["modified_by"] = agent_id

        # Apply updates
        updated_memory = await self.memory_manager.update_memory(memory_id, updates)
        if updated_memory:
            logger.info(
                f"Updated collaborative memory {memory_id} in workspace {workspace_id}"
            )

        return updated_memory

    async def lock_memory(
        self,
        workspace_id: str,
        memory_id: str,
        agent_id: str,
        duration_seconds: int = 300,
    ) -> bool:
        """Lock a memory for exclusive editing.

        Args:
            workspace_id: ID of the workspace
            memory_id: ID of the memory to lock
            agent_id: ID of the agent requesting the lock
            duration_seconds: How long to lock the memory for

        Returns:
            True if the lock was acquired successfully
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return False

        # Check if agent has permission to write
        role = workspace.members[agent_id]
        if role not in [CollaborationRole.OWNER, CollaborationRole.CONTRIBUTOR]:
            return False

        # Check if memory is already locked
        lock = self.locks.get(memory_id)
        if lock and lock["agent_id"] != agent_id and lock["expiry"] > datetime.utcnow():
            return False

        # Set lock
        expiry = datetime.utcnow() + timedelta(seconds=duration_seconds)
        self.locks[memory_id] = {
            "agent_id": agent_id,
            "expiry": expiry,
            "workspace_id": workspace_id,
        }

        # Update memory metadata
        await self.memory_manager.update_memory(
            memory_id, {"locked_by": agent_id, "lock_expiry": expiry}
        )

        logger.info(f"Memory {memory_id} locked by agent {agent_id} until {expiry}")
        return True

    async def unlock_memory(
        self, workspace_id: str, memory_id: str, agent_id: str
    ) -> bool:
        """Unlock a memory.

        Args:
            workspace_id: ID of the workspace
            memory_id: ID of the memory to unlock
            agent_id: ID of the agent releasing the lock

        Returns:
            True if the lock was released successfully
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace:
            return False

        # Check if memory is locked by this agent
        lock = self.locks.get(memory_id)
        if not lock or lock["agent_id"] != agent_id:
            return False

        # Remove lock
        del self.locks[memory_id]

        # Update memory metadata
        await self.memory_manager.update_memory(
            memory_id, {"locked_by": None, "lock_expiry": None}
        )

        logger.info(f"Memory {memory_id} unlocked by agent {agent_id}")
        return True

    async def search_workspace(
        self,
        workspace_id: str,
        agent_id: str,
        query: str,
        max_results: int = 10,
    ) -> List[MemorySearchResult]:
        """Search for memories in a collaborative workspace.

        Args:
            workspace_id: ID of the workspace to search
            agent_id: ID of the agent performing the search
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching memory search results
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return []

        # Search for collaborative memories in this workspace
        results = await self.memory_manager.recall(
            query=query,
            memory_type=MemoryType.COLLABORATIVE,
            max_results=max_results,
        )

        # Filter results to only include memories from this workspace
        filtered_results = [
            result
            for result in results
            if hasattr(result.entry, "metadata") and result.entry.metadata.get("workspace_id") == workspace_id
        ]

        return filtered_results

    async def add_comment(
        self,
        workspace_id: str,
        memory_id: str,
        agent_id: str,
        comment: str,
    ) -> bool:
        """Add a comment to a collaborative memory.

        Args:
            workspace_id: ID of the workspace
            memory_id: ID of the memory to comment on
            agent_id: ID of the agent adding the comment
            comment: The comment text

        Returns:
            True if the comment was added successfully
        """
        workspace = self.workspaces.get(workspace_id)
        if not workspace or agent_id not in workspace.members:
            return False

        # Search for the memory by ID
        results = await self.memory_manager.recall(memory_id)
        if not results:
            return False

        # Find the memory with the matching ID
        memory_result = next((r for r in results if r.entry.id == memory_id), None)
        if not memory_result:
            return False

        memory = memory_result.entry

        # Check if memory belongs to this workspace
        if memory.metadata.get("workspace_id") != workspace_id:
            return False

        # Get existing comments
        comments = memory.metadata.get("comments", [])

        # Add new comment
        comments.append(
            {
                "agent_id": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "text": comment,
            }
        )

        # Update memory with new comments
        await self.memory_manager.update_memory(memory_id, {"comments": comments})
        logger.info(f"Added comment to memory {memory_id} by agent {agent_id}")
        return True

    async def _lock_cleanup_loop(self) -> None:
        """Periodically clean up expired locks."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                now = datetime.utcnow()
                expired_locks = [
                    memory_id
                    for memory_id, lock in self.locks.items()
                    if lock["expiry"] < now
                ]

                for memory_id in expired_locks:
                    # Remove lock
                    lock = self.locks.pop(memory_id)
                    logger.info(
                        f"Expired lock on memory {memory_id} by agent {lock['agent_id']}"
                    )

                    # Update memory metadata
                    await self.memory_manager.update_memory(
                        memory_id, {"locked_by": None, "lock_expiry": None}
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in lock cleanup loop: {str(e)}")
                await asyncio.sleep(10)  # Wait before retrying
