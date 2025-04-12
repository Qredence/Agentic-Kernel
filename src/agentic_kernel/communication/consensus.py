"""Consensus mechanism for multi-agent decision making.

This module implements various consensus mechanisms for agents to reach
agreement on decisions. It supports different voting mechanisms and provides
tools for collecting votes, calculating results, and managing the consensus
process.

Key features:
1. Multiple voting mechanisms (majority, weighted, unanimous)
2. Vote collection and tracking
3. Result calculation with confidence scores
4. Support for minimum participation requirements
"""

import logging
import uuid
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Generic, Set

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type variable for vote options


class VotingMechanism(Enum):
    """Supported voting mechanisms for consensus building."""
    
    MAJORITY = "majority"  # Simple majority vote (>50%)
    WEIGHTED = "weighted"  # Weighted by voter confidence
    UNANIMOUS = "unanimous"  # Requires all votes to agree
    PLURALITY = "plurality"  # Highest vote count wins, even if not majority
    APPROVAL = "approval"  # Voters can approve multiple options
    RANKED_CHOICE = "ranked_choice"  # Voters rank options by preference


class ConsensusVote(Generic[T]):
    """Represents a single vote in a consensus process.
    
    Attributes:
        agent_id: ID of the voting agent
        option: The selected option
        confidence: Confidence level in the vote (0.0-1.0)
        rationale: Explanation for the vote
        timestamp: When the vote was cast
    """
    
    def __init__(
        self,
        agent_id: str,
        option: T,
        confidence: float = 1.0,
        rationale: Optional[str] = None
    ):
        """Initialize a consensus vote.
        
        Args:
            agent_id: ID of the voting agent
            option: The selected option
            confidence: Confidence level in the vote (0.0-1.0)
            rationale: Explanation for the vote
        """
        self.agent_id = agent_id
        self.option = option
        self.confidence = confidence
        self.rationale = rationale
        self.timestamp = datetime.utcnow()


class ConsensusResult(Generic[T]):
    """Represents the result of a consensus process.
    
    Attributes:
        consensus_id: ID of the consensus process
        result: The winning option
        vote_distribution: Distribution of votes across options
        confidence: Overall confidence in the result (0.0-1.0)
        participant_count: Number of agents that participated
        next_steps: Suggested next steps based on the result
    """
    
    def __init__(
        self,
        consensus_id: str,
        result: T,
        vote_distribution: Dict[T, int],
        confidence: float,
        participant_count: int,
        next_steps: Optional[List[str]] = None
    ):
        """Initialize a consensus result.
        
        Args:
            consensus_id: ID of the consensus process
            result: The winning option
            vote_distribution: Distribution of votes across options
            confidence: Overall confidence in the result (0.0-1.0)
            participant_count: Number of agents that participated
            next_steps: Suggested next steps based on the result
        """
        self.consensus_id = consensus_id
        self.result = result
        self.vote_distribution = vote_distribution
        self.confidence = confidence
        self.participant_count = participant_count
        self.next_steps = next_steps or []


class VotingStrategy(ABC, Generic[T]):
    """Abstract base class for voting strategies.
    
    This class defines the interface for different voting mechanisms.
    Subclasses implement specific voting algorithms.
    """
    
    @abstractmethod
    def calculate_result(
        self, votes: List[ConsensusVote[T]]
    ) -> Tuple[Optional[T], Dict[T, int], float]:
        """Calculate the consensus result from a list of votes.
        
        Args:
            votes: List of votes cast by agents
            
        Returns:
            Tuple containing:
            - The winning option (or None if no consensus)
            - Distribution of votes across options
            - Confidence level in the result (0.0-1.0)
        """
        pass


class MajorityVoting(VotingStrategy[T]):
    """Implements majority voting strategy.
    
    An option wins if it receives more than 50% of the votes.
    """
    
    def calculate_result(
        self, votes: List[ConsensusVote[T]]
    ) -> Tuple[Optional[T], Dict[T, int], float]:
        """Calculate result using majority voting.
        
        Args:
            votes: List of votes cast by agents
            
        Returns:
            Tuple containing:
            - The winning option (or None if no majority)
            - Distribution of votes across options
            - Confidence level in the result (0.0-1.0)
        """
        if not votes:
            return None, {}, 0.0
        
        # Count votes for each option
        vote_counts: Dict[T, int] = defaultdict(int)
        for vote in votes:
            vote_counts[vote.option] += 1
        
        # Convert to regular dict for return value
        vote_distribution = dict(vote_counts)
        
        # Find the option with the most votes
        total_votes = len(votes)
        max_votes = 0
        winner = None
        
        for option, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                winner = option
        
        # Check if winner has majority
        if max_votes > total_votes / 2:
            # Calculate confidence based on the margin of victory
            confidence = max_votes / total_votes
            return winner, vote_distribution, confidence
        else:
            # No majority
            return None, vote_distribution, 0.0


class WeightedVoting(VotingStrategy[T]):
    """Implements weighted voting strategy.
    
    Votes are weighted by the confidence level of each voter.
    """
    
    def calculate_result(
        self, votes: List[ConsensusVote[T]]
    ) -> Tuple[Optional[T], Dict[T, int], float]:
        """Calculate result using weighted voting.
        
        Args:
            votes: List of votes cast by agents
            
        Returns:
            Tuple containing:
            - The winning option (or None if no votes)
            - Distribution of votes across options
            - Confidence level in the result (0.0-1.0)
        """
        if not votes:
            return None, {}, 0.0
        
        # Count raw votes for distribution
        vote_counts: Dict[T, int] = defaultdict(int)
        for vote in votes:
            vote_counts[vote.option] += 1
        
        # Convert to regular dict for return value
        vote_distribution = dict(vote_counts)
        
        # Calculate weighted votes
        weighted_votes: Dict[T, float] = defaultdict(float)
        total_weight = 0.0
        
        for vote in votes:
            weighted_votes[vote.option] += vote.confidence
            total_weight += vote.confidence
        
        # Find the option with the highest weighted vote
        max_weighted_votes = 0.0
        winner = None
        
        for option, weight in weighted_votes.items():
            if weight > max_weighted_votes:
                max_weighted_votes = weight
                winner = option
        
        # Calculate confidence based on the proportion of total weight
        confidence = max_weighted_votes / total_weight if total_weight > 0 else 0.0
        
        return winner, vote_distribution, confidence


class UnanimousVoting(VotingStrategy[T]):
    """Implements unanimous voting strategy.
    
    All votes must agree for a decision to be reached.
    """
    
    def calculate_result(
        self, votes: List[ConsensusVote[T]]
    ) -> Tuple[Optional[T], Dict[T, int], float]:
        """Calculate result using unanimous voting.
        
        Args:
            votes: List of votes cast by agents
            
        Returns:
            Tuple containing:
            - The unanimous option (or None if no unanimity)
            - Distribution of votes across options
            - Confidence level in the result (0.0-1.0)
        """
        if not votes:
            return None, {}, 0.0
        
        # Count votes for each option
        vote_counts: Dict[T, int] = defaultdict(int)
        for vote in votes:
            vote_counts[vote.option] += 1
        
        # Convert to regular dict for return value
        vote_distribution = dict(vote_counts)
        
        # Check if all votes are for the same option
        if len(vote_counts) == 1:
            option = next(iter(vote_counts.keys()))
            
            # Calculate average confidence
            avg_confidence = sum(vote.confidence for vote in votes) / len(votes)
            
            return option, vote_distribution, avg_confidence
        else:
            # No unanimity
            return None, vote_distribution, 0.0


class PluralityVoting(VotingStrategy[T]):
    """Implements plurality voting strategy.
    
    The option with the most votes wins, even if not a majority.
    """
    
    def calculate_result(
        self, votes: List[ConsensusVote[T]]
    ) -> Tuple[Optional[T], Dict[T, int], float]:
        """Calculate result using plurality voting.
        
        Args:
            votes: List of votes cast by agents
            
        Returns:
            Tuple containing:
            - The winning option (or None if no votes)
            - Distribution of votes across options
            - Confidence level in the result (0.0-1.0)
        """
        if not votes:
            return None, {}, 0.0
        
        # Count votes for each option
        vote_counts: Dict[T, int] = defaultdict(int)
        for vote in votes:
            vote_counts[vote.option] += 1
        
        # Convert to regular dict for return value
        vote_distribution = dict(vote_counts)
        
        # Find the option with the most votes
        total_votes = len(votes)
        max_votes = 0
        winner = None
        
        for option, count in vote_counts.items():
            if count > max_votes:
                max_votes = count
                winner = option
        
        # Calculate confidence based on the proportion of total votes
        confidence = max_votes / total_votes if total_votes > 0 else 0.0
        
        return winner, vote_distribution, confidence


class ConsensusManager(Generic[T]):
    """Manages the consensus process for multi-agent decision making.
    
    This class tracks consensus requests, collects votes, and calculates
    results using the specified voting mechanism.
    
    Attributes:
        active_consensus: Dictionary of active consensus processes
        voting_strategies: Available voting strategies
    """
    
    def __init__(self):
        """Initialize the consensus manager."""
        self.active_consensus: Dict[str, Dict[str, Any]] = {}
        self.voting_strategies: Dict[VotingMechanism, VotingStrategy[Any]] = {
            VotingMechanism.MAJORITY: MajorityVoting(),
            VotingMechanism.WEIGHTED: WeightedVoting(),
            VotingMechanism.UNANIMOUS: UnanimousVoting(),
            VotingMechanism.PLURALITY: PluralityVoting(),
        }
    
    def create_consensus(
        self,
        topic: str,
        options: List[T],
        participants: List[str],
        voting_mechanism: str = "majority",
        min_participants: int = 1,
        context: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
    ) -> str:
        """Create a new consensus process.
        
        Args:
            topic: The topic requiring consensus
            options: Available options to choose from
            participants: IDs of agents participating in consensus
            voting_mechanism: How votes will be tallied
            min_participants: Minimum number of participants required
            context: Additional context for the decision
            deadline: Optional deadline for voting
            
        Returns:
            ID of the created consensus process
        
        Raises:
            ValueError: If the voting mechanism is not supported
        """
        # Validate voting mechanism
        try:
            mechanism = VotingMechanism(voting_mechanism)
        except ValueError:
            raise ValueError(f"Unsupported voting mechanism: {voting_mechanism}")
        
        # Generate consensus ID
        consensus_id = str(uuid.uuid4())
        
        # Create consensus record
        self.active_consensus[consensus_id] = {
            "topic": topic,
            "options": options,
            "participants": set(participants),
            "voting_mechanism": mechanism,
            "min_participants": min_participants,
            "context": context or {},
            "deadline": deadline,
            "votes": [],
            "voted_agents": set(),
            "created_at": datetime.utcnow(),
        }
        
        logger.info(f"Created consensus process {consensus_id} on topic '{topic}'")
        return consensus_id
    
    def record_vote(
        self,
        consensus_id: str,
        agent_id: str,
        vote: T,
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
            
        Raises:
            ValueError: If the consensus ID is invalid or the agent has already voted
        """
        if consensus_id not in self.active_consensus:
            raise ValueError(f"Invalid consensus ID: {consensus_id}")
        
        consensus = self.active_consensus[consensus_id]
        
        # Check if agent is a participant
        if agent_id not in consensus["participants"]:
            logger.warning(f"Agent {agent_id} is not a participant in consensus {consensus_id}")
            return False
        
        # Check if agent has already voted
        if agent_id in consensus["voted_agents"]:
            raise ValueError(f"Agent {agent_id} has already voted in consensus {consensus_id}")
        
        # Check if vote is valid
        if vote not in consensus["options"]:
            raise ValueError(f"Invalid vote option: {vote}")
        
        # Record the vote
        consensus_vote = ConsensusVote(
            agent_id=agent_id,
            option=vote,
            confidence=confidence,
            rationale=rationale,
        )
        
        consensus["votes"].append(consensus_vote)
        consensus["voted_agents"].add(agent_id)
        
        logger.info(f"Recorded vote from agent {agent_id} in consensus {consensus_id}")
        return True
    
    def check_consensus_status(
        self, consensus_id: str
    ) -> Tuple[bool, Optional[ConsensusResult[T]]]:
        """Check if consensus has been reached.
        
        Args:
            consensus_id: ID of the consensus process
            
        Returns:
            Tuple containing:
            - Boolean indicating if consensus is complete
            - ConsensusResult if complete, None otherwise
            
        Raises:
            ValueError: If the consensus ID is invalid
        """
        if consensus_id not in self.active_consensus:
            raise ValueError(f"Invalid consensus ID: {consensus_id}")
        
        consensus = self.active_consensus[consensus_id]
        votes = consensus["votes"]
        
        # Check if minimum participation requirement is met
        if len(votes) < consensus["min_participants"]:
            return False, None
        
        # Check if all participants have voted
        if len(votes) < len(consensus["participants"]):
            # Not everyone has voted yet
            # Check if deadline has passed
            if consensus["deadline"] and datetime.utcnow() > consensus["deadline"]:
                # Deadline passed, calculate with available votes
                pass
            else:
                # Still waiting for votes
                return False, None
        
        # Calculate result using the specified voting mechanism
        mechanism = consensus["voting_mechanism"]
        strategy = self.voting_strategies[mechanism]
        
        result, vote_distribution, confidence = strategy.calculate_result(votes)
        
        # Check if a result was determined
        if result is None:
            return False, None
        
        # Create consensus result
        consensus_result = ConsensusResult(
            consensus_id=consensus_id,
            result=result,
            vote_distribution=vote_distribution,
            confidence=confidence,
            participant_count=len(consensus["voted_agents"]),
        )
        
        # Mark consensus as complete
        consensus["completed"] = True
        consensus["result"] = consensus_result
        
        logger.info(f"Consensus reached in process {consensus_id} with result: {result}")
        return True, consensus_result
    
    def get_consensus_info(self, consensus_id: str) -> Dict[str, Any]:
        """Get information about a consensus process.
        
        Args:
            consensus_id: ID of the consensus process
            
        Returns:
            Dictionary with consensus information
            
        Raises:
            ValueError: If the consensus ID is invalid
        """
        if consensus_id not in self.active_consensus:
            raise ValueError(f"Invalid consensus ID: {consensus_id}")
        
        consensus = self.active_consensus[consensus_id]
        
        # Create a copy with serializable types
        info = {
            "topic": consensus["topic"],
            "options": consensus["options"],
            "participants": list(consensus["participants"]),
            "voting_mechanism": consensus["voting_mechanism"].value,
            "min_participants": consensus["min_participants"],
            "context": consensus["context"],
            "deadline": consensus["deadline"].isoformat() if consensus["deadline"] else None,
            "created_at": consensus["created_at"].isoformat(),
            "vote_count": len(consensus["votes"]),
            "voted_agents": list(consensus["voted_agents"]),
        }
        
        # Add result if available
        if "completed" in consensus and consensus["completed"]:
            result = consensus["result"]
            info["completed"] = True
            info["result"] = result.result
            info["vote_distribution"] = result.vote_distribution
            info["confidence"] = result.confidence
        else:
            info["completed"] = False
        
        return info
    
    def close_consensus(self, consensus_id: str) -> None:
        """Close a consensus process and remove it from active tracking.
        
        Args:
            consensus_id: ID of the consensus process to close
            
        Raises:
            ValueError: If the consensus ID is invalid
        """
        if consensus_id not in self.active_consensus:
            raise ValueError(f"Invalid consensus ID: {consensus_id}")
        
        del self.active_consensus[consensus_id]
        logger.info(f"Closed consensus process {consensus_id}")