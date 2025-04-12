"""Protocol extensions for collaborative operations.

This module extends the communication protocol with methods for
collaborative operations, including memory management and consensus building,
allowing agents to create and manage shared memory workspaces and
collaborate on complex reasoning tasks.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..memory.collaborative import CollaborationRole
from .consensus import ConsensusManager, ConsensusResult, VotingMechanism
from .message import MessagePriority, MessageType
from .protocol import CommunicationProtocol


class CollaborativeProtocol:
    """Extension of the communication protocol for collaborative operations.

    This class provides methods for sending messages related to collaborative
    operations, including memory management and consensus building,
    extending the base CommunicationProtocol.
    """

    def __init__(self, protocol: CommunicationProtocol):
        """Initialize the collaborative protocol extension.

        Args:
            protocol: The base communication protocol to extend
        """
        self.protocol = protocol
        self.consensus_manager = ConsensusManager()

    async def create_workspace(
        self,
        recipient: str,
        name: str,
        description: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Send a message to create a new collaborative workspace.

        Args:
            recipient: ID of the agent that will create the workspace
            name: Name of the workspace
            description: Description of the workspace
            tags: Optional tags for categorization

        Returns:
            The message ID of the workspace creation message
        """
        content = {
            "name": name,
            "description": description,
            "tags": tags or [],
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.WORKSPACE_CREATE,
            content=content,
        )

    async def join_workspace(
        self,
        recipient: str,
        workspace_id: str,
        requested_role: Optional[str] = None,
    ) -> str:
        """Send a message to join an existing workspace.

        Args:
            recipient: ID of the workspace owner or manager
            workspace_id: ID of the workspace to join
            requested_role: Optional role the agent is requesting

        Returns:
            The message ID of the workspace join message
        """
        content = {
            "workspace_id": workspace_id,
            "requested_role": requested_role,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.WORKSPACE_JOIN,
            content=content,
        )

    async def leave_workspace(
        self,
        recipient: str,
        workspace_id: str,
        reason: Optional[str] = None,
    ) -> str:
        """Send a message to leave a workspace.

        Args:
            recipient: ID of the workspace owner or manager
            workspace_id: ID of the workspace to leave
            reason: Optional reason for leaving

        Returns:
            The message ID of the workspace leave message
        """
        content = {
            "workspace_id": workspace_id,
            "reason": reason,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.WORKSPACE_LEAVE,
            content=content,
        )

    async def invite_to_workspace(
        self,
        recipient: str,
        workspace_id: str,
        workspace_name: str,
        role: str,
        invitation_message: Optional[str] = None,
    ) -> str:
        """Send a message to invite an agent to a workspace.

        Args:
            recipient: ID of the agent being invited
            workspace_id: ID of the workspace
            workspace_name: Name of the workspace
            role: Role being offered to the invited agent
            invitation_message: Optional message to the invited agent

        Returns:
            The message ID of the workspace invitation message
        """
        content = {
            "workspace_id": workspace_id,
            "workspace_name": workspace_name,
            "role": role,
            "invitation_message": invitation_message,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.WORKSPACE_INVITE,
            content=content,
        )

    async def store_memory(
        self,
        recipient: str,
        workspace_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a message to store a memory in a workspace.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            content: Content of the memory
            tags: Optional tags for categorization
            importance: Importance score (0-1)
            metadata: Additional metadata

        Returns:
            The message ID of the memory store message
        """
        message_content = {
            "workspace_id": workspace_id,
            "content": content,
            "tags": tags or [],
            "importance": importance,
            "metadata": metadata or {},
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_STORE,
            content=message_content,
        )

    async def retrieve_memory(
        self,
        recipient: str,
        workspace_id: str,
        memory_id: str,
    ) -> str:
        """Send a message to retrieve a memory from a workspace.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            memory_id: ID of the memory to retrieve

        Returns:
            The message ID of the memory retrieve message
        """
        content = {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_RETRIEVE,
            content=content,
        )

    async def update_memory(
        self,
        recipient: str,
        workspace_id: str,
        memory_id: str,
        updates: Dict[str, Any],
    ) -> str:
        """Send a message to update a memory in a workspace.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            memory_id: ID of the memory to update
            updates: Updates to apply to the memory

        Returns:
            The message ID of the memory update message
        """
        content = {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
            "updates": updates,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_UPDATE,
            content=content,
        )

    async def lock_memory(
        self,
        recipient: str,
        workspace_id: str,
        memory_id: str,
        duration_seconds: int = 300,
    ) -> str:
        """Send a message to lock a memory for exclusive editing.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            memory_id: ID of the memory to lock
            duration_seconds: How long to lock the memory for

        Returns:
            The message ID of the memory lock message
        """
        content = {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
            "duration_seconds": duration_seconds,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_LOCK,
            content=content,
        )

    async def unlock_memory(
        self,
        recipient: str,
        workspace_id: str,
        memory_id: str,
    ) -> str:
        """Send a message to unlock a memory.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            memory_id: ID of the memory to unlock

        Returns:
            The message ID of the memory unlock message
        """
        content = {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_UNLOCK,
            content=content,
        )

    async def comment_on_memory(
        self,
        recipient: str,
        workspace_id: str,
        memory_id: str,
        comment: str,
    ) -> str:
        """Send a message to comment on a memory.

        Args:
            recipient: ID of the agent managing the workspace
            workspace_id: ID of the workspace
            memory_id: ID of the memory to comment on
            comment: The comment text

        Returns:
            The message ID of the memory comment message
        """
        content = {
            "workspace_id": workspace_id,
            "memory_id": memory_id,
            "comment": comment,
        }

        return await self.protocol.send_message(
            recipient=recipient,
            message_type=MessageType.MEMORY_COMMENT,
            content=content,
        )

    # Consensus-related methods

    async def create_consensus_process(
        self,
        recipients: List[str],
        topic: str,
        options: List[Any],
        context: Dict[str, Any],
        voting_mechanism: str = "majority",
        min_participants: int = 1,
        voting_deadline: Optional[datetime] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Create a new consensus process and send requests to participants.

        Args:
            recipients: IDs of the agents to participate in consensus
            topic: The topic requiring consensus
            options: Available options to choose from
            context: Context information for the decision
            voting_mechanism: How votes will be tallied (majority, weighted, unanimous)
            min_participants: Minimum number of participants required
            voting_deadline: Optional deadline for voting

        Returns:
            Tuple containing:
            - The consensus ID
            - Dictionary mapping recipient IDs to message IDs
        """
        # Create consensus process in the manager
        consensus_id = self.consensus_manager.create_consensus(
            topic=topic,
            options=options,
            participants=recipients,
            voting_mechanism=voting_mechanism,
            min_participants=min_participants,
            context=context,
            deadline=voting_deadline,
        )

        # Send consensus request messages to all participants
        content = {
            "consensus_id": consensus_id,
            "topic": topic,
            "options": options,
            "context": context,
            "voting_deadline": voting_deadline.isoformat() if voting_deadline else None,
            "voting_mechanism": voting_mechanism,
            "min_participants": min_participants,
        }

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.protocol.send_message(
                recipient=recipient,
                message_type=MessageType.CONSENSUS_REQUEST,
                content=content,
                priority=MessagePriority.NORMAL,
            )
            message_ids[recipient] = message_id

        return consensus_id, message_ids

    async def record_consensus_vote(
        self,
        consensus_id: str,
        agent_id: str,
        vote: Any,
        confidence: float = 1.0,
        rationale: Optional[str] = None,
    ) -> bool:
        """Record a vote in a consensus process.

        Args:
            consensus_id: ID of the consensus process
            agent_id: ID of the voting agent
            vote: The agent's vote
            confidence: Confidence level in the vote (0.0-1.0)
            rationale: Explanation for the vote

        Returns:
            True if the vote was recorded, False otherwise
        """
        try:
            return self.consensus_manager.record_vote(
                consensus_id=consensus_id,
                agent_id=agent_id,
                vote=vote,
                confidence=confidence,
                rationale=rationale,
            )
        except ValueError as e:
            # Log the error and return False
            print(f"Error recording vote: {str(e)}")
            return False

    async def check_consensus_status(
        self, consensus_id: str
    ) -> Tuple[bool, Optional[ConsensusResult]]:
        """Check if consensus has been reached.

        Args:
            consensus_id: ID of the consensus process

        Returns:
            Tuple containing:
            - Boolean indicating if consensus is complete
            - ConsensusResult if complete, None otherwise
        """
        try:
            return self.consensus_manager.check_consensus_status(consensus_id)
        except ValueError as e:
            # Log the error and return False, None
            print(f"Error checking consensus status: {str(e)}")
            return False, None

    async def get_consensus_info(self, consensus_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a consensus process.

        Args:
            consensus_id: ID of the consensus process

        Returns:
            Dictionary with consensus information, or None if not found
        """
        try:
            return self.consensus_manager.get_consensus_info(consensus_id)
        except ValueError as e:
            # Log the error and return None
            print(f"Error getting consensus info: {str(e)}")
            return None

    async def send_consensus_result(
        self,
        consensus_id: str,
        recipients: List[str],
        result: Any,
        vote_distribution: Dict[Any, int],
        confidence: float,
        next_steps: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Send the result of a consensus process to participants.

        Args:
            consensus_id: ID of the consensus process
            recipients: IDs of the agents that participated in consensus
            result: The consensus result
            vote_distribution: Distribution of votes
            confidence: Overall confidence in the result
            next_steps: Any actions to be taken based on the result

        Returns:
            Dictionary mapping recipient IDs to message IDs
        """
        content = {
            "consensus_id": consensus_id,
            "result": result,
            "vote_distribution": vote_distribution,
            "confidence": confidence,
            "next_steps": next_steps or [],
        }

        # Send to all recipients
        message_ids = {}
        for recipient in recipients:
            message_id = await self.protocol.send_message(
                recipient=recipient,
                message_type=MessageType.CONSENSUS_RESULT,
                content=content,
                priority=MessagePriority.NORMAL,
            )
            message_ids[recipient] = message_id

        return message_ids

    async def process_consensus_vote(
        self,
        message_id: str,
        sender: str,
        consensus_id: str,
        vote: Any,
        confidence: float,
        rationale: Optional[str] = None,
    ) -> None:
        """Process a consensus vote message and update the consensus state.

        Args:
            message_id: ID of the vote message
            sender: ID of the voting agent
            consensus_id: ID of the consensus process
            vote: The agent's vote
            confidence: Confidence level in the vote
            rationale: Explanation for the vote
        """
        # Record the vote
        recorded = await self.record_consensus_vote(
            consensus_id=consensus_id,
            agent_id=sender,
            vote=vote,
            confidence=confidence,
            rationale=rationale,
        )

        if not recorded:
            # Vote could not be recorded
            return

        # Check if consensus has been reached
        consensus_complete, consensus_result = await self.check_consensus_status(consensus_id)

        if consensus_complete and consensus_result:
            # Get consensus info to find all participants
            consensus_info = await self.get_consensus_info(consensus_id)
            if not consensus_info:
                return

            # Send result to all participants
            participants = consensus_info.get("participants", [])
            await self.send_consensus_result(
                consensus_id=consensus_id,
                recipients=participants,
                result=consensus_result.result,
                vote_distribution=consensus_result.vote_distribution,
                confidence=consensus_result.confidence,
                next_steps=consensus_result.next_steps,
            )

            # Close the consensus process
            self.consensus_manager.close_consensus(consensus_id)
