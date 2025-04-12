"""Custom exceptions for the Agentic-Kernel system.

This module defines custom exceptions used throughout the system to provide
more specific error handling and better error messages.

Example:
    ```python
    try:
        task = manager.get_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
    except TaskNotFoundError as e:
        logger.error(str(e))
    ```
"""

from enum import Enum
from typing import Dict, List, Optional, Any


class ErrorSeverity(Enum):
    """Severity levels for errors in the system.

    These levels help categorize errors by their impact and urgency.
    """

    DEBUG = "debug"  # Informational, not impacting functionality
    INFO = "info"  # Informational, minor impact
    WARNING = "warning"  # Potential issue, functionality degraded
    ERROR = "error"  # Serious issue, functionality broken
    CRITICAL = "critical"  # System-wide failure


class ErrorCategory(Enum):
    """Categories of errors in the system.

    These categories help organize errors by their domain or source.
    """

    TASK = "task"  # Task-related errors
    AGENT = "agent"  # Agent-related errors
    COMMUNICATION = "communication"  # Communication-related errors
    CONSENSUS = "consensus"  # Consensus-related errors
    CAPABILITY = "capability"  # Capability-related errors
    PLUGIN = "plugin"  # Plugin-related errors
    SECURITY = "security"  # Security-related errors
    SYSTEM = "system"  # System-level errors
    VALIDATION = "validation"  # Validation errors
    RESOURCE = "resource"  # Resource-related errors


class AgenticKernelError(Exception):
    """Base exception class for all Agentic-Kernel errors.

    This class serves as the parent for all custom exceptions in the system.
    It provides a consistent interface and helps with error categorization.

    Attributes:
        message (str): Human-readable error description
        code (Optional[str]): Error code for programmatic handling
        severity (ErrorSeverity): Severity level of the error
        category (ErrorCategory): Category of the error
        details (Dict[str, Any]): Additional error details
        recovery_hints (List[str]): Suggestions for recovering from the error
        retry_possible (bool): Whether retry is possible for this error
    """

    def __init__(
        self, 
        message: str, 
        code: str = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = False
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description
            code: Optional error code for programmatic handling
            severity: Severity level of the error
            category: Category of the error
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        self.message = message
        self.code = code
        self.severity = severity
        self.category = category
        self.details = details or {}
        self.recovery_hints = recovery_hints or []
        self.retry_possible = retry_possible
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the exception to a dictionary.

        Returns:
            Dictionary representation of the exception
        """
        return {
            "message": self.message,
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category.value,
            "details": self.details,
            "recovery_hints": self.recovery_hints,
            "retry_possible": self.retry_possible
        }


# Task-related exceptions

class TaskNotFoundError(AgenticKernelError):
    """Raised when attempting to access a task that doesn't exist.

    This exception is raised when trying to perform operations on a task
    that cannot be found in the system, either because it was never created
    or has been removed.

    Example:
        ```python
        if task_id not in active_tasks:
            raise TaskNotFoundError(
                f"Task {task_id} not found in active tasks",
                code="TASK_404"
            )
        ```
    """

    def __init__(
        self, 
        message: str, 
        code: str = "TASK_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of which task was not found and why
            code: Error code, defaults to "TASK_NOT_FOUND"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=False
        )


class TaskExecutionError(AgenticKernelError):
    """Raised when a task fails during execution.

    This exception provides details about what went wrong during task execution,
    including the specific error encountered and any relevant context.

    Example:
        ```python
        try:
            result = await agent.execute_task(task)
        except Exception as e:
            raise TaskExecutionError(
                f"Failed to execute task {task.id}: {str(e)}",
                code="TASK_EXEC_ERROR"
            )
        ```
    """

    def __init__(
        self, 
        message: str, 
        code: str = "TASK_EXECUTION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of what went wrong during execution
            code: Error code, defaults to "TASK_EXECUTION_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.TASK,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


# Agent-related exceptions

class AgentError(AgenticKernelError):
    """Raised for errors related to agent operations (e.g., registration, configuration)."""

    def __init__(
        self, 
        message: str, 
        code: str = "AGENT_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = False
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the agent error
            code: Error code, defaults to "AGENT_ERROR"
            severity: Severity level of the error
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=severity,
            category=ErrorCategory.AGENT,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class AgentNotFoundError(AgentError):
    """Raised when attempting to access an agent that doesn't exist."""

    def __init__(
        self, 
        message: str, 
        code: str = "AGENT_NOT_FOUND",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of which agent was not found and why
            code: Error code, defaults to "AGENT_NOT_FOUND"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=False
        )


class AgentCapabilityError(AgentError):
    """Raised when an agent lacks a required capability."""

    def __init__(
        self, 
        message: str, 
        code: str = "AGENT_CAPABILITY_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the missing capability
            code: Error code, defaults to "AGENT_CAPABILITY_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=False
        )


# Communication-related exceptions

class CommunicationError(AgenticKernelError):
    """Base class for communication-related errors."""

    def __init__(
        self, 
        message: str, 
        code: str = "COMMUNICATION_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the communication error
            code: Error code, defaults to "COMMUNICATION_ERROR"
            severity: Severity level of the error
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=severity,
            category=ErrorCategory.COMMUNICATION,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class MessageDeliveryError(CommunicationError):
    """Raised when a message cannot be delivered to its recipient."""

    def __init__(
        self, 
        message: str, 
        code: str = "MESSAGE_DELIVERY_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the delivery error
            code: Error code, defaults to "MESSAGE_DELIVERY_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class MessageTimeoutError(CommunicationError):
    """Raised when a message response times out."""

    def __init__(
        self, 
        message: str, 
        code: str = "MESSAGE_TIMEOUT_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the timeout error
            code: Error code, defaults to "MESSAGE_TIMEOUT_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.WARNING,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class MessageValidationError(CommunicationError):
    """Raised when a message fails validation."""

    def __init__(
        self, 
        message: str, 
        code: str = "MESSAGE_VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = False
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the validation error
            code: Error code, defaults to "MESSAGE_VALIDATION_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class ProtocolError(CommunicationError):
    """Raised when there's an error in the communication protocol."""

    def __init__(
        self, 
        message: str, 
        code: str = "PROTOCOL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = False
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the protocol error
            code: Error code, defaults to "PROTOCOL_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


# Consensus-related exceptions

class ConsensusError(AgenticKernelError):
    """Base class for consensus-related errors."""

    def __init__(
        self, 
        message: str, 
        code: str = "CONSENSUS_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the consensus error
            code: Error code, defaults to "CONSENSUS_ERROR"
            severity: Severity level of the error
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=severity,
            category=ErrorCategory.CONSENSUS,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class ConsensusNotReachedError(ConsensusError):
    """Raised when consensus cannot be reached."""

    def __init__(
        self, 
        message: str, 
        code: str = "CONSENSUS_NOT_REACHED",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = True
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of why consensus was not reached
            code: Error code, defaults to "CONSENSUS_NOT_REACHED"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.WARNING,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


# System-level exceptions

class SystemError(AgenticKernelError):
    """Raised for general system-level errors (e.g., configuration, initialization)."""

    def __init__(
        self, 
        message: str, 
        code: str = "SYSTEM_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None,
        retry_possible: bool = False
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the system error
            code: Error code, defaults to "SYSTEM_ERROR"
            severity: Severity level of the error
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
            retry_possible: Whether retry is possible for this error
        """
        super().__init__(
            message, 
            code, 
            severity=severity,
            category=ErrorCategory.SYSTEM,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=retry_possible
        )


class ConfigurationError(SystemError):
    """Raised when there's an error in the system configuration."""

    def __init__(
        self, 
        message: str, 
        code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_hints: Optional[List[str]] = None
    ) -> None:
        """Initialize the exception.

        Args:
            message: Description of the configuration error
            code: Error code, defaults to "CONFIGURATION_ERROR"
            details: Additional error details
            recovery_hints: Suggestions for recovering from the error
        """
        super().__init__(
            message, 
            code, 
            severity=ErrorSeverity.ERROR,
            details=details,
            recovery_hints=recovery_hints,
            retry_possible=False
        )
