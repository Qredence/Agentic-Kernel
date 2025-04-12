"""Handler for collaborative memory operations.

This module provides a handler for collaborative memory operations,
processing incoming messages and interacting with the CollaborativeMemoryManager.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..communication.message import Message, MessageType
from ..communication.protocol import CommunicationProtocol
from .collaborative import CollaborationRole, CollaborativeMemoryManager

logger = logging.getLogger(__name__)


class CollaborativeMemoryHandler:
    """Handler for collaborative memory operations.

    This class processes incoming messages related to collaborative memory
    operations and interacts with the CollaborativeMemoryManager.

    Attributes:
        memory_manager: The collaborative memory manager
        protocol: The communication protocol
        agent_id: ID of the agent using this handler
    """

    def __init__(
        self,
        memory_manager: CollaborativeMemoryManager,
        protocol: CommunicationProtocol,
        agent_id: str,
    ):
        """Initialize the collaborative memory handler.

        Args:
            memory_manager: The collaborative memory manager
            protocol: The communication protocol
            agent_id: ID of the agent using this handler
        """
        self.memory_manager = memory_manager
        self.protocol = protocol
        self.agent_id = agent_id

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register handlers for collaborative memory messages."""
        self.protocol.register_handler(
            MessageType.WORKSPACE_CREATE, self._handle_workspace_create
        )
        self.protocol.register_handler(
            MessageType.WORKSPACE_JOIN, self._handle_workspace_join
        )
        self.protocol.register_handler(
            MessageType.WORKSPACE_LEAVE, self._handle_workspace_leave
        )
        self.protocol.register_handler(
            MessageType.WORKSPACE_INVITE, self._handle_workspace_invite
        )
        self.protocol.register_handler(
            MessageType.MEMORY_STORE, self._handle_memory_store
        )
        self.protocol.register_handler(
            MessageType.MEMORY_RETRIEVE, self._handle_memory_retrieve
        )
        self.protocol.register_handler(
            MessageType.MEMORY_UPDATE, self._handle_memory_update
        )
        self.protocol.register_handler(
            MessageType.MEMORY_LOCK, self._handle_memory_lock
        )
        self.protocol.register_handler(
            MessageType.MEMORY_UNLOCK, self._handle_memory_unlock
        )
        self.protocol.register_handler(
            MessageType.MEMORY_COMMENT, self._handle_memory_comment
        )

    async def _handle_workspace_create(self, message: Message):
        """Handle a workspace creation message.

        Args:
            message: The workspace creation message
        """
        try:
            # Extract message content
            name = message.content.get("name")
            description = message.content.get("description", "")
            tags = message.content.get("tags", [])

            # Create the workspace
            workspace = await self.memory_manager.create_workspace(
                name=name,
                description=description,
                created_by=message.sender,
                tags=tags,
            )

            # Send response
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.TASK_RESPONSE,
                content={
                    "status": "success",
                    "result": {
                        "workspace_id": workspace.id,
                        "name": workspace.name,
                        "description": workspace.description,
                        "created_by": workspace.created_by,
                        "created_at": workspace.created_at.isoformat(),
                    },
                },
                correlation_id=message.message_id,
            )

        except Exception as e:
            logger.error(f"Error handling workspace create: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "workspace_creation_failed",
                    "description": f"Failed to create workspace: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_workspace_join(self, message: Message):
        """Handle a workspace join message.

        Args:
            message: The workspace join message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            requested_role = message.content.get("requested_role")

            # Get the workspace
            workspace = await self.memory_manager.get_workspace(workspace_id)
            if not workspace:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "workspace_not_found",
                        "description": f"Workspace {workspace_id} not found",
                    },
                    correlation_id=message.message_id,
                )
                return

            # Check if the agent is already a member
            if message.sender in workspace.members:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "workspace_id": workspace.id,
                            "name": workspace.name,
                            "role": workspace.members[message.sender],
                            "message": "Already a member of this workspace",
                        },
                    },
                    correlation_id=message.message_id,
                )
                return

            # Check if the current agent is the owner or has permission to add members
            if (
                self.agent_id not in workspace.members
                or workspace.members[self.agent_id] != CollaborationRole.OWNER
            ):
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "permission_denied",
                        "description": "You don't have permission to add members to this workspace",
                    },
                    correlation_id=message.message_id,
                )
                return

            # Determine the role to assign
            role = (
                CollaborationRole(requested_role)
                if requested_role
                else CollaborationRole.CONTRIBUTOR
            )

            # Add the agent to the workspace
            success = await self.memory_manager.add_member(
                workspace_id=workspace_id, agent_id=message.sender, role=role
            )

            if success:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "workspace_id": workspace.id,
                            "name": workspace.name,
                            "role": role,
                            "message": f"Added to workspace with role {role}",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "join_failed",
                        "description": "Failed to join workspace",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling workspace join: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "join_failed",
                    "description": f"Failed to join workspace: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_workspace_leave(self, message: Message):
        """Handle a workspace leave message.

        Args:
            message: The workspace leave message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")

            # Get the workspace
            workspace = await self.memory_manager.get_workspace(workspace_id)
            if not workspace:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "workspace_not_found",
                        "description": f"Workspace {workspace_id} not found",
                    },
                    correlation_id=message.message_id,
                )
                return

            # Check if the agent is a member
            if message.sender not in workspace.members:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "not_a_member",
                        "description": "You are not a member of this workspace",
                    },
                    correlation_id=message.message_id,
                )
                return

            # Remove the agent from the workspace
            success = await self.memory_manager.remove_member(
                workspace_id=workspace_id, agent_id=message.sender
            )

            if success:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "workspace_id": workspace.id,
                            "name": workspace.name,
                            "message": "Successfully left the workspace",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "leave_failed",
                        "description": "Failed to leave workspace",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling workspace leave: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "leave_failed",
                    "description": f"Failed to leave workspace: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_workspace_invite(self, message: Message):
        """Handle a workspace invitation message.

        Args:
            message: The workspace invitation message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            workspace_name = message.content.get("workspace_name")
            role = message.content.get("role")
            invitation_message = message.content.get("invitation_message")

            # This agent has received an invitation to join a workspace
            # Respond with acceptance (in a real system, this might involve user interaction)
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.TASK_RESPONSE,
                content={
                    "status": "success",
                    "result": {
                        "workspace_id": workspace_id,
                        "accepted": True,
                        "message": f"Accepted invitation to join workspace {workspace_name}",
                    },
                },
                correlation_id=message.message_id,
            )

            # Send a join request to formalize the membership
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.WORKSPACE_JOIN,
                content={
                    "workspace_id": workspace_id,
                    "requested_role": role,
                },
            )

        except Exception as e:
            logger.error(f"Error handling workspace invitation: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "invitation_processing_failed",
                    "description": f"Failed to process invitation: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_store(self, message: Message):
        """Handle a memory store message.

        Args:
            message: The memory store message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            content = message.content.get("content")
            tags = message.content.get("tags", [])
            importance = message.content.get("importance", 0.5)
            metadata = message.content.get("metadata", {})

            # Store the memory
            memory_id = await self.memory_manager.store_memory(
                workspace_id=workspace_id,
                agent_id=message.sender,
                content=content,
                tags=tags,
                importance=importance,
                metadata=metadata,
            )

            if memory_id:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": memory_id,
                            "workspace_id": workspace_id,
                            "message": "Memory stored successfully",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "memory_store_failed",
                        "description": "Failed to store memory",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory store: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "memory_store_failed",
                    "description": f"Failed to store memory: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_retrieve(self, message: Message):
        """Handle a memory retrieve message.

        Args:
            message: The memory retrieve message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            memory_id = message.content.get("memory_id")

            # Retrieve the memory
            memory = await self.memory_manager.get_memory(
                workspace_id=workspace_id,
                memory_id=memory_id,
                agent_id=message.sender,
            )

            if memory:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": memory.id,
                            "content": memory.content,
                            "memory_type": memory.memory_type,
                            "timestamp": memory.timestamp.isoformat(),
                            "last_accessed": memory.last_accessed.isoformat(),
                            "agent_id": memory.agent_id,
                            "importance": memory.importance,
                            "tags": memory.tags,
                            "metadata": memory.metadata,
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "memory_not_found",
                        "description": f"Memory {memory_id} not found or not accessible",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory retrieve: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "memory_retrieve_failed",
                    "description": f"Failed to retrieve memory: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_update(self, message: Message):
        """Handle a memory update message.

        Args:
            message: The memory update message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            memory_id = message.content.get("memory_id")
            updates = message.content.get("updates", {})

            # Update the memory
            updated_memory = await self.memory_manager.update_memory(
                workspace_id=workspace_id,
                memory_id=memory_id,
                agent_id=message.sender,
                updates=updates,
            )

            if updated_memory:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": updated_memory.id,
                            "workspace_id": workspace_id,
                            "message": "Memory updated successfully",
                            "version": updated_memory.metadata.get("version"),
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "memory_update_failed",
                        "description": "Failed to update memory",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory update: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "memory_update_failed",
                    "description": f"Failed to update memory: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_lock(self, message: Message):
        """Handle a memory lock message.

        Args:
            message: The memory lock message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            memory_id = message.content.get("memory_id")
            duration_seconds = message.content.get("duration_seconds", 300)

            # Lock the memory
            success = await self.memory_manager.lock_memory(
                workspace_id=workspace_id,
                memory_id=memory_id,
                agent_id=message.sender,
                duration_seconds=duration_seconds,
            )

            if success:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": memory_id,
                            "workspace_id": workspace_id,
                            "message": f"Memory locked for {duration_seconds} seconds",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "memory_lock_failed",
                        "description": "Failed to lock memory",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory lock: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "memory_lock_failed",
                    "description": f"Failed to lock memory: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_unlock(self, message: Message):
        """Handle a memory unlock message.

        Args:
            message: The memory unlock message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            memory_id = message.content.get("memory_id")

            # Unlock the memory
            success = await self.memory_manager.unlock_memory(
                workspace_id=workspace_id,
                memory_id=memory_id,
                agent_id=message.sender,
            )

            if success:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": memory_id,
                            "workspace_id": workspace_id,
                            "message": "Memory unlocked successfully",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "memory_unlock_failed",
                        "description": "Failed to unlock memory",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory unlock: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "memory_unlock_failed",
                    "description": f"Failed to unlock memory: {str(e)}",
                },
                correlation_id=message.message_id,
            )

    async def _handle_memory_comment(self, message: Message):
        """Handle a memory comment message.

        Args:
            message: The memory comment message
        """
        try:
            # Extract message content
            workspace_id = message.content.get("workspace_id")
            memory_id = message.content.get("memory_id")
            comment = message.content.get("comment")

            # Add the comment
            success = await self.memory_manager.add_comment(
                workspace_id=workspace_id,
                memory_id=memory_id,
                agent_id=message.sender,
                comment=comment,
            )

            if success:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.TASK_RESPONSE,
                    content={
                        "status": "success",
                        "result": {
                            "memory_id": memory_id,
                            "workspace_id": workspace_id,
                            "message": "Comment added successfully",
                        },
                    },
                    correlation_id=message.message_id,
                )
            else:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.ERROR,
                    content={
                        "error_type": "comment_failed",
                        "description": "Failed to add comment",
                    },
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling memory comment: {str(e)}")
            await self.protocol.send_message(
                recipient=message.sender,
                message_type=MessageType.ERROR,
                content={
                    "error_type": "comment_failed",
                    "description": f"Failed to add comment: {str(e)}",
                },
                correlation_id=message.message_id,
            )
