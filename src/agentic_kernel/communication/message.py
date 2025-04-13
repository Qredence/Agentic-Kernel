"""Message types and protocols for agent communication.

This module defines the core message types and protocols used for communication
between agents in the Agentic-Kernel system.

Key features:
1. Standardized message format
2. Type-safe message construction
3. Protocol definitions
4. Message validation
5. Serialization support
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Set

from pydantic import BaseModel, Field, root_validator, validator

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages that can be exchanged between agents."""

    # Core message types
    TASK_REQUEST = "task_request"  # Request another agent to perform a task
    TASK_RESPONSE = "task_response"  # Response to a task request
    QUERY = "query"  # Query for information
    QUERY_RESPONSE = "query_response"  # Response to a query
    STATUS_UPDATE = "status_update"  # Agent status update
    ERROR = "error"  # Error notification

    # A2A-specific message types
    CAPABILITY_REQUEST = "capability_request"  # Request for agent capabilities
    CAPABILITY_RESPONSE = "capability_response"  # Response with agent capabilities
    AGENT_DISCOVERY = "agent_discovery"  # Agent discovery and registration message
    CONSENSUS_REQUEST = "consensus_request"  # Request for consensus on a decision
    CONSENSUS_VOTE = "consensus_vote"  # Vote in a consensus process
    CONSENSUS_RESULT = "consensus_result"  # Result of a consensus process
    CONFLICT_NOTIFICATION = "conflict_notification"  # Notification of a conflict
    CONFLICT_RESOLUTION = "conflict_resolution"  # Resolution of a conflict
    FEEDBACK = "feedback"  # Feedback on agent performance
    COORDINATION_REQUEST = "coordination_request"  # Request for coordination
    COORDINATION_RESPONSE = "coordination_response"  # Response to coordination request
    TASK_DECOMPOSITION = "task_decomposition"  # Decomposition of a task into subtasks

    # Collaborative memory operations
    WORKSPACE_CREATE = "workspace_create"  # Create a new workspace
    WORKSPACE_JOIN = "workspace_join"  # Join an existing workspace
    WORKSPACE_LEAVE = "workspace_leave"  # Leave a workspace
    WORKSPACE_INVITE = "workspace_invite"  # Invite an agent to a workspace
    MEMORY_STORE = "memory_store"  # Store a memory in a workspace
    MEMORY_RETRIEVE = "memory_retrieve"  # Retrieve a memory from a workspace
    MEMORY_UPDATE = "memory_update"  # Update a memory in a workspace
    MEMORY_LOCK = "memory_lock"  # Lock a memory for exclusive editing
    MEMORY_UNLOCK = "memory_unlock"  # Unlock a memory
    MEMORY_COMMENT = "memory_comment"  # Comment on a memory


class MessagePriority(Enum):
    """Priority levels for messages."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    """Base message type for agent communication.

    This class defines the standard structure for all messages exchanged
    between agents in the system, with enhanced support for A2A-style protocols.

    Attributes:
        message_id: Unique identifier for the message
        message_type: Type of message
        sender: ID of the sending agent
        recipient: ID of the receiving agent
        content: Message payload
        priority: Message priority level
        timestamp: When the message was created
        correlation_id: ID to link related messages
        metadata: Additional message metadata

        # A2A-specific attributes
        conversation_id: ID for grouping messages in a conversation thread
        sender_capabilities: Capabilities of the sending agent
        trust_level: Trust level between sender and recipient
        collaboration_context: Context for collaborative reasoning
        ttl: Time-to-live for message validity
        requires_acknowledgment: Whether the message requires acknowledgment
        routing_path: Path the message has taken through the agent network
    """

    # Class variables for validation
    # A2A capability types based on Google's A2A standard
    # https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
    A2A_CAPABILITY_TYPES: ClassVar[Set[str]] = {
        # Core capabilities
        "reasoning",
        "planning",
        "learning",
        "perception",
        "memory",
        "communication",
        "action",
        "coordination",
        "problem_solving",
        "decision_making",
        "creativity",
        "social_intelligence",
        "emotional_intelligence",
        # A2A-specific capabilities
        "capability_discovery",
        "agent_discovery",
        "consensus_building",
        "conflict_resolution",
        "feedback_processing",
        "task_decomposition",
        "collaborative_memory",
    }

    # Required fields
    message_id: str = Field(..., description="Unique identifier for the message")
    message_type: MessageType = Field(..., description="Type of message")
    sender: str = Field(..., description="ID of the sending agent")
    recipient: str = Field(..., description="ID of the receiving agent")
    content: Dict[str, Any] = Field(..., description="Message payload")

    # Optional fields with defaults
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = Field(
        None, description="ID to link related messages"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # A2A-specific fields
    conversation_id: Optional[str] = Field(
        None, description="ID for grouping messages in a conversation thread"
    )
    sender_capabilities: Optional[List[str]] = Field(
        None, description="Capabilities of the sending agent"
    )
    trust_level: Optional[float] = Field(
        None, description="Trust level between sender and recipient (0.0-1.0)"
    )
    collaboration_context: Optional[Dict[str, Any]] = Field(
        None, description="Context for collaborative reasoning"
    )
    ttl: Optional[int] = Field(
        None, description="Time-to-live for message validity in seconds"
    )
    requires_acknowledgment: bool = Field(
        False, description="Whether the message requires acknowledgment"
    )
    routing_path: List[str] = Field(
        default_factory=list,
        description="Path the message has taken through the agent network",
    )

    @validator("trust_level")
    def validate_trust_level(cls, v: Optional[float]) -> Optional[float]:
        """Validate that trust_level is between 0.0 and 1.0."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("Trust level must be between 0.0 and 1.0")
        return v

    @validator("sender_capabilities")
    def validate_capabilities(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that capabilities are from the known set."""
        if v is not None:
            unknown_capabilities = [
                cap for cap in v if cap not in cls.A2A_CAPABILITY_TYPES
            ]
            if unknown_capabilities:
                logger.warning(
                    f"Unknown capabilities in message: {unknown_capabilities}. "
                    f"Known capabilities are: {cls.A2A_CAPABILITY_TYPES}"
                )
        return v

    @validator("ttl")
    def validate_ttl(cls, v: Optional[int]) -> Optional[int]:
        """Validate that TTL is positive."""
        if v is not None and v <= 0:
            raise ValueError("TTL must be positive")
        return v

    @root_validator(skip_on_failure=True)
    def validate_a2a_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate A2A-specific fields based on message type."""
        message_type = values.get("message_type")

        # For A2A-specific message types, certain fields are recommended
        if message_type in [
            MessageType.CAPABILITY_REQUEST,
            MessageType.CAPABILITY_RESPONSE,
            MessageType.CONSENSUS_REQUEST,
            MessageType.CONSENSUS_VOTE,
            MessageType.CONSENSUS_RESULT,
            MessageType.CONFLICT_NOTIFICATION,
            MessageType.CONFLICT_RESOLUTION,
            MessageType.FEEDBACK,
            MessageType.COORDINATION_REQUEST,
            MessageType.COORDINATION_RESPONSE,
            MessageType.TASK_DECOMPOSITION,
        ]:
            # Check for conversation_id
            if not values.get("conversation_id"):
                logger.warning(
                    f"A2A message of type {message_type.value} should have a conversation_id"
                )

            # For capability-related messages, sender_capabilities should be provided
            if message_type in [
                MessageType.CAPABILITY_RESPONSE,
                MessageType.AGENT_DISCOVERY,
            ]:
                if not values.get("sender_capabilities"):
                    logger.warning(
                        f"A2A message of type {message_type.value} should include sender_capabilities"
                    )

            # For consensus and conflict messages, collaboration_context should be provided
            if message_type in [
                MessageType.CONSENSUS_REQUEST,
                MessageType.CONSENSUS_VOTE,
                MessageType.CONSENSUS_RESULT,
                MessageType.CONFLICT_NOTIFICATION,
                MessageType.CONFLICT_RESOLUTION,
            ]:
                if not values.get("collaboration_context"):
                    logger.warning(
                        f"A2A message of type {message_type.value} should include collaboration_context"
                    )

        return values

    def add_to_routing_path(self, agent_id: str) -> None:
        """Add an agent ID to the routing path.

        Args:
            agent_id: ID of the agent to add to the routing path
        """
        if agent_id not in self.routing_path:
            self.routing_path.append(agent_id)

    def is_a2a_message(self) -> bool:
        """Check if this is an A2A-specific message type.

        Returns:
            bool: True if this is an A2A-specific message type
        """
        return self.message_type in [
            MessageType.CAPABILITY_REQUEST,
            MessageType.CAPABILITY_RESPONSE,
            MessageType.AGENT_DISCOVERY,
            MessageType.CONSENSUS_REQUEST,
            MessageType.CONSENSUS_VOTE,
            MessageType.CONSENSUS_RESULT,
            MessageType.CONFLICT_NOTIFICATION,
            MessageType.CONFLICT_RESOLUTION,
            MessageType.FEEDBACK,
            MessageType.COORDINATION_REQUEST,
            MessageType.COORDINATION_RESPONSE,
            MessageType.TASK_DECOMPOSITION,
        ]


class TaskRequest(Message):
    """Message for requesting task execution from another agent.

    This message type is used when one agent needs another agent to perform
    a specific task.

    The content field should contain:
    - task_description: Description of the task to perform
    - parameters: Task parameters
    - constraints: Any constraints on execution
    - deadline: Optional deadline for completion
    """

    message_type: MessageType = MessageType.TASK_REQUEST


class TaskResponse(Message):
    """Message for responding to a task request.

    This message type is used to return the results of a requested task
    execution.

    The content field should contain:
    - status: Task execution status
    - result: Task execution result
    - error: Error information if task failed
    - metrics: Performance metrics
    """

    message_type: MessageType = MessageType.TASK_RESPONSE


class Query(Message):
    """Message for querying information from another agent.

    This message type is used when one agent needs to request information
    from another agent.

    The content field should contain:
    - query: The query string or structured query
    - context: Any relevant context for the query
    - required_format: Optional format for the response
    """

    message_type: MessageType = MessageType.QUERY


class QueryResponse(Message):
    """Message for responding to an information query.

    This message type is used to return the requested information to
    a querying agent.

    The content field should contain:
    - result: The query result
    - confidence: Confidence level in the result
    - source: Source of the information
    """

    message_type: MessageType = MessageType.QUERY_RESPONSE


class StatusUpdate(Message):
    """Message for providing status updates.

    This message type is used to inform other agents about changes in
    an agent's status or state.

    The content field should contain:
    - status: Current status
    - details: Status details
    - resources: Available resources
    """

    message_type: MessageType = MessageType.STATUS_UPDATE


class ErrorMessage(Message):
    """Message for communicating errors.

    This message type is used to inform other agents about errors
    that have occurred.

    The content field should contain:
    - error_type: Type of error
    - description: Error description
    - stack_trace: Optional stack trace
    - recovery_hints: Optional recovery suggestions
    """

    message_type: MessageType = MessageType.ERROR


class AgentDiscoveryMessage(Message):
    """Message for agent discovery and registration.

    This message type is used when agents announce their presence,
    capabilities, and availability to the system.

    The content field should contain:
    - agent_id: Unique identifier for the agent
    - agent_type: Type/role of the agent
    - capabilities: List of agent capabilities
    - status: Current operational status
    - resources: Available resources and constraints
    - metadata: Additional agent-specific information
    """

    message_type: MessageType = MessageType.AGENT_DISCOVERY


class CapabilityRequestMessage(Message):
    """Message for requesting capabilities from another agent.

    This message type is used when an agent wants to discover
    what capabilities another agent has.

    The content field should contain:
    - capability_types: Optional list of capability types to filter by
    - detail_level: Level of detail requested (basic, detailed, full)
    """

    message_type: MessageType = MessageType.CAPABILITY_REQUEST


class CapabilityResponseMessage(Message):
    """Message for responding to a capability request.

    This message type is used to provide information about an agent's
    capabilities to a requesting agent.

    The content field should contain:
    - capabilities: List of capability descriptions
    - performance_metrics: Optional metrics for each capability
    - limitations: Any limitations or constraints on capabilities
    """

    message_type: MessageType = MessageType.CAPABILITY_RESPONSE


class ConsensusRequestMessage(Message):
    """Message for requesting consensus on a decision.

    This message type is used when an agent needs to build consensus
    among multiple agents for a decision.

    The content field should contain:
    - topic: The topic requiring consensus
    - options: Available options to choose from
    - context: Context information for the decision
    - voting_deadline: Deadline for voting
    - voting_mechanism: How votes will be tallied (majority, weighted, unanimous)
    - min_participants: Minimum number of participants required
    """

    message_type: MessageType = MessageType.CONSENSUS_REQUEST


class ConsensusVoteMessage(Message):
    """Message for voting in a consensus process.

    This message type is used when an agent casts a vote in response
    to a consensus request.

    The content field should contain:
    - consensus_id: ID of the consensus request
    - vote: The agent's vote
    - confidence: Confidence level in the vote (0.0-1.0)
    - rationale: Explanation for the vote
    """

    message_type: MessageType = MessageType.CONSENSUS_VOTE


class ConsensusResultMessage(Message):
    """Message for announcing the result of a consensus process.

    This message type is used to inform agents about the outcome
    of a consensus building process.

    The content field should contain:
    - consensus_id: ID of the consensus request
    - result: The consensus result
    - vote_distribution: Distribution of votes
    - confidence: Overall confidence in the result
    - next_steps: Any actions to be taken based on the result
    """

    message_type: MessageType = MessageType.CONSENSUS_RESULT


class ConflictNotificationMessage(Message):
    """Message for notifying about a conflict.

    This message type is used when an agent detects a conflict
    that needs resolution.

    The content field should contain:
    - conflict_type: Type of conflict
    - description: Description of the conflict
    - parties: Agents involved in the conflict
    - impact: Impact assessment of the conflict
    - resolution_deadline: Deadline for resolution
    """

    message_type: MessageType = MessageType.CONFLICT_NOTIFICATION


class ConflictResolutionMessage(Message):
    """Message for resolving a conflict.

    This message type is used to propose or announce a resolution
    to a conflict.

    The content field should contain:
    - conflict_id: ID of the conflict being resolved
    - resolution: The proposed resolution
    - rationale: Explanation for the resolution
    - required_actions: Actions required from involved parties
    - verification_method: How to verify the conflict is resolved
    """

    message_type: MessageType = MessageType.CONFLICT_RESOLUTION


class FeedbackMessage(Message):
    """Message for providing feedback on agent performance.

    This message type is used to give feedback to an agent about
    its performance or behavior.

    The content field should contain:
    - feedback_type: Type of feedback (performance, behavior, outcome)
    - rating: Numerical rating (if applicable)
    - description: Detailed feedback description
    - improvement_suggestions: Suggestions for improvement
    - context: Context in which the feedback applies
    """

    message_type: MessageType = MessageType.FEEDBACK


class CoordinationRequestMessage(Message):
    """Message for requesting coordination with other agents.

    This message type is used when an agent needs to coordinate
    its activities with other agents.

    The content field should contain:
    - coordination_type: Type of coordination needed
    - activities: Activities requiring coordination
    - constraints: Timing or resource constraints
    - dependencies: Dependencies on other agents or activities
    - priority: Priority of the coordination request
    """

    message_type: MessageType = MessageType.COORDINATION_REQUEST


class CoordinationResponseMessage(Message):
    """Message for responding to a coordination request.

    This message type is used to respond to a request for coordination
    from another agent.

    The content field should contain:
    - coordination_id: ID of the coordination request
    - response: Accept, reject, or propose alternative
    - availability: Agent's availability for coordination
    - conditions: Any conditions for coordination
    - proposed_schedule: Proposed timing for coordinated activities
    """

    message_type: MessageType = MessageType.COORDINATION_RESPONSE


class TaskDecompositionMessage(Message):
    """Message for decomposing a task into subtasks.

    This message type is used when an agent breaks down a complex task
    into smaller, more manageable subtasks.

    The content field should contain:
    - parent_task_id: ID of the parent task
    - subtasks: List of subtask descriptions
    - dependencies: Dependencies between subtasks
    - allocation_suggestions: Suggestions for which agents should handle which subtasks
    - estimated_complexity: Complexity assessment for each subtask
    """

    message_type: MessageType = MessageType.TASK_DECOMPOSITION
