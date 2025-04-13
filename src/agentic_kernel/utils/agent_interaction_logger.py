"""Agent interaction logging utilities.

This module provides specialized logging utilities for multi-agent interactions
in the Agentic-Kernel system. It extends the base logging functionality to support
structured logging of agent messages, conversations, and interaction patterns.

Key features:
1. Agent message logging
2. Conversation thread tracking
3. Interaction metrics collection
4. Structured logging formats for agent interactions
5. Integration with the existing logging system
"""

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from ..communication.message import Message
from .logging import JsonFormatter, LogMetrics, get_logger

# Create a specialized logger for agent interactions
agent_interaction_logger = get_logger("agent_interactions")


class AgentInteractionLogger:
    """Logger for agent interactions and communications.
    
    This class provides specialized logging for agent-to-agent interactions,
    with support for tracking conversation threads, message exchanges, and
    interaction metrics.
    
    Attributes:
        name: Name for the logger instance
        logger: Underlying logger instance
        metrics: Metrics collector for interaction statistics
        conversation_contexts: Dictionary of active conversation contexts
    """
    
    def __init__(self, name: str = "agent_interactions"):
        """Initialize the agent interaction logger.
        
        Args:
            name: Name for the logger instance
        """
        self.name = name
        self.logger = get_logger(name)
        self.metrics = LogMetrics(f"{name}.metrics")
        self.conversation_contexts: dict[str, dict[str, Any]] = {}
    
    def log_message(
        self, 
        message: Message, 
        direction: str = "sent", 
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log an agent message.
        
        Args:
            message: The message to log
            direction: Direction of the message ("sent" or "received")
            extra: Additional context to include in the log
        """
        if not isinstance(message, Message):
            self.logger.warning(
                f"Attempted to log non-Message object: {type(message)}",
            )
            return
            
        # Create a structured log entry for the message
        log_entry = {
            "message_id": message.message_id,
            "message_type": message.message_type.value,
            "sender": message.sender,
            "recipient": message.recipient,
            "direction": direction,
            "timestamp": datetime.utcnow().isoformat(),
            "priority": message.priority.value,
        }
        
        # Add conversation tracking if available
        if message.conversation_id:
            log_entry["conversation_id"] = message.conversation_id
            
            # Update conversation context if this is a new conversation
            if message.conversation_id not in self.conversation_contexts:
                self.conversation_contexts[message.conversation_id] = {
                    "start_time": datetime.utcnow().isoformat(),
                    "participants": {message.sender, message.recipient},
                    "message_count": 1,
                    "last_activity": datetime.utcnow().isoformat(),
                    "message_types": {message.message_type.value},
                }
            else:
                # Update existing conversation context
                context = self.conversation_contexts[message.conversation_id]
                context["participants"].add(message.sender)
                context["participants"].add(message.recipient)
                context["message_count"] += 1
                context["last_activity"] = datetime.utcnow().isoformat()
                context["message_types"].add(message.message_type.value)
        
        # Add any extra context
        if extra:
            log_entry.update(extra)
        
        # Log the message
        self.logger.info(
            f"Agent {direction} message: {message.message_type.value}",
            extra={"agent_message": log_entry},
        )
        
        # Update metrics
        self.metrics.increment(f"messages_{direction}")
        self.metrics.increment(f"message_type_{message.message_type.value}")
        
        # Special handling for A2A-specific message types
        if message.is_a2a_message():
            self.metrics.increment("a2a_messages")
    
    def log_conversation_summary(self, conversation_id: str) -> None:
        """Log a summary of a conversation.
        
        Args:
            conversation_id: ID of the conversation to summarize
        """
        if conversation_id not in self.conversation_contexts:
            self.logger.warning(f"Attempted to summarize unknown conversation: {conversation_id}")
            return
            
        context = self.conversation_contexts[conversation_id]
        
        # Create a summary log entry
        summary = {
            "conversation_id": conversation_id,
            "duration": self._calculate_duration(
                context["start_time"], 
                context["last_activity"],
            ),
            "message_count": context["message_count"],
            "participants": list(context["participants"]),
            "message_types": list(context["message_types"]),
        }
        
        self.logger.info(
            f"Conversation summary: {conversation_id}",
            extra={"conversation_summary": summary},
        )
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """Calculate the duration between two ISO format timestamps.
        
        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format
            
        Returns:
            float: Duration in seconds
        """
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        return (end - start).total_seconds()
    
    @contextmanager
    def conversation_scope(
        self, 
        conversation_id: str, 
        initiator: str, 
        responder: str,
        topic: str | None = None,
    ):
        """Context manager for tracking a conversation between agents.
        
        Args:
            conversation_id: ID for the conversation
            initiator: ID of the initiating agent
            responder: ID of the responding agent
            topic: Optional topic for the conversation
            
        Yields:
            AgentInteractionLogger: This logger instance
        """
        # Initialize conversation context
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = {
                "start_time": datetime.utcnow().isoformat(),
                "participants": {initiator, responder},
                "message_count": 0,
                "last_activity": datetime.utcnow().isoformat(),
                "message_types": set(),
                "topic": topic,
            }
            
        self.logger.info(
            f"Starting conversation: {conversation_id}",
            extra={
                "conversation_start": {
                    "conversation_id": conversation_id,
                    "initiator": initiator,
                    "responder": responder,
                    "topic": topic,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            },
        )
        
        try:
            yield self
        finally:
            # Log conversation summary when scope exits
            self.log_conversation_summary(conversation_id)
    
    def log_interaction_event(
        self, 
        event_type: str, 
        agents: list[str], 
        details: dict[str, Any],
    ) -> None:
        """Log a general agent interaction event.
        
        Args:
            event_type: Type of interaction event
            agents: List of agent IDs involved
            details: Details about the interaction
        """
        self.logger.info(
            f"Agent interaction event: {event_type}",
            extra={
                "interaction_event": {
                    "event_type": event_type,
                    "agents": agents,
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": details,
                },
            },
        )
        
        # Update metrics
        self.metrics.increment(f"interaction_event_{event_type}")
    
    def log_metrics(self) -> None:
        """Log collected metrics for agent interactions."""
        self.metrics.log_metrics()


# Global instance for convenience
interaction_logger = AgentInteractionLogger()


@contextmanager
def agent_interaction_scope(
    initiator: str, 
    responder: str, 
    topic: str | None = None,
    conversation_id: str | None = None,
):
    """Context manager for tracking agent interactions.
    
    This is a convenience wrapper around AgentInteractionLogger.conversation_scope.
    
    Args:
        initiator: ID of the initiating agent
        responder: ID of the responding agent
        topic: Optional topic for the interaction
        conversation_id: Optional ID for the conversation (generated if not provided)
        
    Yields:
        AgentInteractionLogger: The interaction logger instance
    """
    conv_id = conversation_id or str(uuid.uuid4())
    
    with interaction_logger.conversation_scope(
        conv_id, initiator, responder, topic,
    ) as logger:
        yield logger


def log_agent_message(
    message: Message, 
    direction: str = "sent", 
    extra: dict[str, Any] | None = None,
) -> None:
    """Convenience function to log an agent message.
    
    Args:
        message: The message to log
        direction: Direction of the message ("sent" or "received")
        extra: Additional context to include in the log
    """
    interaction_logger.log_message(message, direction, extra)


def setup_agent_interaction_logging(
    log_level: str | int = logging.INFO,
    log_file: str | None = None,
    use_json: bool = True,
) -> None:
    """Set up logging specifically for agent interactions.
    
    Args:
        log_level: Logging level to use
        log_file: Optional path to log file
        use_json: Whether to use JSON formatting
    """
    # Create a specialized handler for agent interactions
    handler = logging.StreamHandler()
    
    if use_json:
        formatter = JsonFormatter(
            default_fields={
                "timestamp": "created",
                "level": "levelname",
                "name": "name",
                "agent_interaction": True,
            },
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        
    handler.setFormatter(formatter)
    
    # Configure the agent interaction logger
    logger = logging.getLogger("agent_interactions")
    logger.setLevel(log_level)
    logger.addHandler(handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    logger.info("Agent interaction logging initialized")