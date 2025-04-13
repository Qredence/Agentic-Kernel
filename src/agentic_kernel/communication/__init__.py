"""Communication module for agent interactions.

This module provides the communication infrastructure for agents to interact
with each other, including message passing, capability advertisement, and
agent discovery.

Key components:
1. Message types and protocols
2. Capability registry for agent capabilities
3. Dynamic agent discovery and capability advertisement
4. Communication protocols for reliable message delivery
"""

# Import message types
# Import capability registry
from .capability_registry import (
    AgentCapability,
    AgentInfo,
    CapabilityRegistry,
)

# Import dynamic capability registry
from .dynamic_capability_registry import (
    AgentPresenceMonitor,
    CapabilitySubscription,
    DynamicCapabilityRegistry,
)
from .message import (
    AgentDiscoveryMessage,
    CapabilityRequestMessage,
    CapabilityResponseMessage,
    ConflictNotificationMessage,
    ConflictResolutionMessage,
    ConsensusRequestMessage,
    ConsensusResultMessage,
    ConsensusVoteMessage,
    CoordinationRequestMessage,
    CoordinationResponseMessage,
    DeliveryConfirmationMessage,
    ErrorMessage,
    FeedbackMessage,
    Message,
    MessageAckMessage,
    MessagePriority,
    MessageRetryMessage,
    MessageType,
    Query,
    QueryResponse,
    StatusUpdate,
    TaskDecompositionMessage,
    TaskRequest,
    TaskResponse,
)

# Import communication protocol
from .protocol import CommunicationProtocol

__all__ = [
    # Message types
    "Message",
    "MessageType",
    "MessagePriority",
    "TaskRequest",
    "TaskResponse",
    "Query",
    "QueryResponse",
    "StatusUpdate",
    "ErrorMessage",
    "AgentDiscoveryMessage",
    "CapabilityRequestMessage",
    "CapabilityResponseMessage",
    "ConsensusRequestMessage",
    "ConsensusVoteMessage",
    "ConsensusResultMessage",
    "ConflictNotificationMessage",
    "ConflictResolutionMessage",
    "FeedbackMessage",
    "CoordinationRequestMessage",
    "CoordinationResponseMessage",
    "TaskDecompositionMessage",
    "MessageAckMessage",
    "DeliveryConfirmationMessage",
    "MessageRetryMessage",
    
    # Capability registry
    "AgentCapability",
    "AgentInfo",
    "CapabilityRegistry",
    
    # Dynamic capability registry
    "CapabilitySubscription",
    "AgentPresenceMonitor",
    "DynamicCapabilityRegistry",
    
    # Communication protocol
    "CommunicationProtocol",
]