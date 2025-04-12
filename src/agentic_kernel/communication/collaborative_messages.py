"""Message types for collaborative memory operations.

This module defines message types for collaborative memory operations,
allowing agents to create and manage shared memory workspaces and
collaborate on complex reasoning tasks.

Key features:
1. Workspace creation and management
2. Collaborative memory operations
3. Synchronization and locking
4. Access control and permissions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .message import Message, MessageType

# Message types for collaborative memory operations are defined in message.py


class WorkspaceCreateMessage(Message):
    """Message for creating a new collaborative workspace.

    This message type is used when an agent wants to create a new
    workspace for collaborative reasoning.

    The content field should contain:
    - name: Name of the workspace
    - description: Description of the workspace
    - tags: Optional tags for categorization
    """

    message_type: MessageType = MessageType.WORKSPACE_CREATE


class WorkspaceJoinMessage(Message):
    """Message for joining an existing workspace.

    This message type is used when an agent wants to join an
    existing collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace to join
    - requested_role: Role the agent is requesting (if applicable)
    """

    message_type: MessageType = MessageType.WORKSPACE_JOIN


class WorkspaceLeaveMessage(Message):
    """Message for leaving a workspace.

    This message type is used when an agent wants to leave a
    collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace to leave
    - reason: Optional reason for leaving
    """

    message_type: MessageType = MessageType.WORKSPACE_LEAVE


class WorkspaceInviteMessage(Message):
    """Message for inviting an agent to a workspace.

    This message type is used when an agent wants to invite another
    agent to join a collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace
    - workspace_name: Name of the workspace
    - role: Role being offered to the invited agent
    - invitation_message: Optional message to the invited agent
    """

    message_type: MessageType = MessageType.WORKSPACE_INVITE


class MemoryStoreMessage(Message):
    """Message for storing a memory in a workspace.

    This message type is used when an agent wants to store a new
    memory in a collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace
    - content: Content of the memory
    - tags: Optional tags for categorization
    - importance: Importance score (0-1)
    - metadata: Additional metadata
    """

    message_type: MessageType = MessageType.MEMORY_STORE


class MemoryRetrieveMessage(Message):
    """Message for retrieving a memory from a workspace.

    This message type is used when an agent wants to retrieve a
    memory from a collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace
    - memory_id: ID of the memory to retrieve
    """

    message_type: MessageType = MessageType.MEMORY_RETRIEVE


class MemoryUpdateMessage(Message):
    """Message for updating a memory in a workspace.

    This message type is used when an agent wants to update a
    memory in a collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace
    - memory_id: ID of the memory to update
    - updates: Updates to apply to the memory
    """

    message_type: MessageType = MessageType.MEMORY_UPDATE


class MemoryLockMessage(Message):
    """Message for locking a memory for exclusive editing.

    This message type is used when an agent wants to lock a memory
    for exclusive editing.

    The content field should contain:
    - workspace_id: ID of the workspace
    - memory_id: ID of the memory to lock
    - duration_seconds: How long to lock the memory for
    """

    message_type: MessageType = MessageType.MEMORY_LOCK


class MemoryUnlockMessage(Message):
    """Message for unlocking a memory.

    This message type is used when an agent wants to release a lock
    on a memory.

    The content field should contain:
    - workspace_id: ID of the workspace
    - memory_id: ID of the memory to unlock
    """

    message_type: MessageType = MessageType.MEMORY_UNLOCK


class MemoryCommentMessage(Message):
    """Message for commenting on a memory.

    This message type is used when an agent wants to add a comment
    to a memory in a collaborative workspace.

    The content field should contain:
    - workspace_id: ID of the workspace
    - memory_id: ID of the memory to comment on
    - comment: The comment text
    """

    message_type: MessageType = MessageType.MEMORY_COMMENT
