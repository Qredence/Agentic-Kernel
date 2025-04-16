"""
Consensus mechanisms for agent collaboration.

This module contains classes and methods for building consensus among
agents, including requesting consensus, voting, and handling consensus
results.
"""

from datetime import datetime
from typing import Any

from ...communication.collaborative_protocol import CollaborativeProtocol
from ...communication.message import Message, MessageType
from .base_agent import BaseAgent


class ConsensusMixin:
    """
    Mixin class providing consensus-building functionality for agents.
    
    This mixin provides methods for requesting consensus from other agents,
    handling consensus requests, and managing consensus voting.
    """
    
    def _handle_consensus_request(self, message: Message) -> None:
        """
        Handle a consensus request message.
        
        Args:
            message: The consensus request message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        self.logger.info(f"Received consensus request from {message.sender_id}")
        
        try:
            # Extract consensus request details
            consensus_id = message.content.get("consensus_id", "")
            topic = message.content.get("topic", "")
            options = message.content.get("options", [])
            context = message.content.get("context", {})
            
            # Process the consensus request (this would typically involve some decision-making logic)
            # For now, we'll just select the first option as a placeholder
            selected_option = options[0] if options else None
            confidence = 0.8  # Example confidence value
            rationale = "This option seems most appropriate based on the context."
            
            # Send vote
            self.send_consensus_vote(
                request_id=message.message_id,
                recipient=message.sender_id,
                consensus_id=consensus_id,
                vote=selected_option,
                confidence=confidence,
                rationale=rationale,
            )
            
        except Exception as e:
            self.logger.error(f"Error handling consensus request: {str(e)}")
            # Optionally send an error response

    def _handle_consensus_vote(self, message: Message) -> None:
        """
        Handle a consensus vote message.
        
        Args:
            message: The consensus vote message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        self.logger.info(f"Received consensus vote from {message.sender_id}")
        
        try:
            # Extract vote details
            consensus_id = message.content.get("consensus_id", "")
            vote = message.content.get("vote")
            confidence = message.content.get("confidence", 1.0)
            rationale = message.content.get("rationale", "")
            
            # Store the vote (in a real implementation, this would update some consensus tracking)
            # For now, we'll just log it
            self.logger.info(
                f"Vote for consensus {consensus_id}: {vote} (confidence: {confidence})",
            )
            self.logger.info(f"Rationale: {rationale}")
            
            # Check if we have a collaborative protocol to track consensus
            if hasattr(self, "collaborative_protocol") and isinstance(
                self.collaborative_protocol, CollaborativeProtocol,
            ):
                self.collaborative_protocol.record_vote(
                    consensus_id, message.sender_id, vote, confidence, rationale,
                )
                
                # Check if consensus is reached
                if self.collaborative_protocol.is_consensus_reached(consensus_id):
                    result = self.collaborative_protocol.get_consensus_result(consensus_id)
                    self._send_consensus_result(consensus_id, result)
            
        except Exception as e:
            self.logger.error(f"Error handling consensus vote: {str(e)}")

    def _handle_consensus_result(self, message: Message) -> None:
        """
        Handle a consensus result message.
        
        Args:
            message: The consensus result message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        self.logger.info(f"Received consensus result from {message.sender_id}")
        
        try:
            # Extract result details
            consensus_id = message.content.get("consensus_id", "")
            result = message.content.get("result")
            voting_summary = message.content.get("voting_summary", {})
            
            # Process the consensus result (in a real implementation, this might trigger actions)
            # For now, we'll just log it
            self.logger.info(f"Consensus {consensus_id} result: {result}")
            self.logger.info(f"Voting summary: {voting_summary}")
            
        except Exception as e:
            self.logger.error(f"Error handling consensus result: {str(e)}")

    def request_consensus(
        self,
        recipients: list[str],
        topic: str,
        options: list[Any],
        context: dict[str, Any] | None = None,
        voting_mechanism: str = "majority",
        min_participants: int = 1,
        voting_deadline: datetime | None = None,
    ) -> str:
        """
        Request consensus from a group of agents.
        
        Args:
            recipients: List of agent IDs to request consensus from
            topic: The topic or question for consensus
            options: List of options to choose from
            context: Optional context information
            voting_mechanism: Mechanism to determine consensus (e.g., "majority", "unanimous")
            min_participants: Minimum number of participants required
            voting_deadline: Optional deadline for voting
            
        Returns:
            The consensus ID
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        # Generate consensus ID
        consensus_id = f"consensus_{self.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Initialize collaborative protocol if needed
        if not hasattr(self, "collaborative_protocol") or not isinstance(
            self.collaborative_protocol, CollaborativeProtocol,
        ):
            self.collaborative_protocol = CollaborativeProtocol()
            
        # Register consensus request
        self.collaborative_protocol.register_consensus(
            consensus_id=consensus_id,
            topic=topic,
            options=options,
            participants=recipients,
            voting_mechanism=voting_mechanism,
            min_participants=min_participants,
            deadline=voting_deadline,
        )
        
        # Send consensus request to each recipient
        for recipient_id in recipients:
            message = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=recipient_id,
                message_type=MessageType.CONSENSUS_REQUEST,
                content={
                    "consensus_id": consensus_id,
                    "topic": topic,
                    "options": options,
                    "context": context or {},
                    "voting_mechanism": voting_mechanism,
                    "deadline": voting_deadline.isoformat() if voting_deadline else None,
                },
            )
            
            self.message_bus.send_message(message)
            
        self.logger.info(f"Sent consensus request to {len(recipients)} agents")
        
        return consensus_id

    def send_consensus_vote(
        self,
        request_id: str,
        recipient: str,
        consensus_id: str,
        vote: Any,
        confidence: float = 1.0,
        rationale: str | None = None,
    ) -> str:
        """
        Send a vote for a consensus request.
        
        Args:
            request_id: The ID of the original request message
            recipient: ID of the agent that requested consensus
            consensus_id: The consensus ID
            vote: The selected option
            confidence: Confidence level in the vote (0.0 to 1.0)
            rationale: Optional explanation for the vote
            
        Returns:
            The message ID of the vote
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        # Create vote message
        message = self.protocol.create_message(
            sender_id=self.id,
            recipient_id=recipient,
            message_type=MessageType.CONSENSUS_VOTE,
            content={
                "consensus_id": consensus_id,
                "vote": vote,
                "confidence": confidence,
                "rationale": rationale or "",
            },
            reference_message_id=request_id,
        )
        
        # Send the message
        self.message_bus.send_message(message)
        self.logger.info(f"Sent consensus vote to {recipient}")
        
        return message.message_id

    def _send_consensus_result(self, consensus_id: str, result: Any) -> None:
        """
        Send the result of a consensus process to all participants.
        
        Args:
            consensus_id: The consensus ID
            result: The consensus result
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        if not hasattr(self, "collaborative_protocol") or not isinstance(
            self.collaborative_protocol, CollaborativeProtocol,
        ):
            self.logger.error("Collaborative protocol is required to send consensus results")
            return
            
        # Get consensus details
        consensus_info = self.collaborative_protocol.get_consensus_info(consensus_id)
        if not consensus_info:
            self.logger.error(f"No consensus information found for ID {consensus_id}")
            return
            
        # Get voting summary
        voting_summary = self.collaborative_protocol.get_voting_summary(consensus_id)
        
        # Send result to all participants
        for participant_id in consensus_info.get("participants", []):
            message = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=participant_id,
                message_type=MessageType.CONSENSUS_RESULT,
                content={
                    "consensus_id": consensus_id,
                    "result": result,
                    "voting_summary": voting_summary,
                },
            )
            
            self.message_bus.send_message(message)
            
        self.logger.info(f"Sent consensus result to {len(consensus_info.get('participants', []))} agents")

    def check_consensus_status(self, consensus_id: str) -> dict[str, Any]:
        """
        Check the status of a consensus process.
        
        Args:
            consensus_id: The consensus ID
            
        Returns:
            Dictionary with consensus status information
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("ConsensusMixin must be used with BaseAgent")
            
        if not hasattr(self, "collaborative_protocol") or not isinstance(
            self.collaborative_protocol, CollaborativeProtocol,
        ):
            return {
                "status": "error",
                "message": "Collaborative protocol is not initialized",
            }
            
        # Get consensus details
        consensus_info = self.collaborative_protocol.get_consensus_info(consensus_id)
        if not consensus_info:
            return {
                "status": "error",
                "message": f"No consensus information found for ID {consensus_id}",
            }
            
        # Get voting summary
        voting_summary = self.collaborative_protocol.get_voting_summary(consensus_id)
        
        # Check if consensus is reached
        is_reached = self.collaborative_protocol.is_consensus_reached(consensus_id)
        result = None
        if is_reached:
            result = self.collaborative_protocol.get_consensus_result(consensus_id)
            
        return {
            "status": "reached" if is_reached else "in_progress",
            "consensus_id": consensus_id,
            "topic": consensus_info.get("topic", ""),
            "voting_mechanism": consensus_info.get("voting_mechanism", ""),
            "participants": consensus_info.get("participants", []),
            "votes_received": len(voting_summary),
            "voting_summary": voting_summary,
            "result": result,
        }