"""Error handling utilities for agent communication.

This module provides standardized error handling utilities for agent
communication, including error logging, recovery suggestions, and
retry mechanisms.

Key features:
1. Standardized error handling for agent interactions
2. Error logging with appropriate severity levels
3. Recovery suggestion generation
4. Retry mechanisms for transient errors
5. Error message formatting for agent communication
"""

import asyncio
import logging
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

from ..exceptions import (
    AgenticKernelError,
    CommunicationError,
    ErrorSeverity,
    MessageDeliveryError,
    MessageTimeoutError,
    MessageValidationError,
    ProtocolError,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Return type for functions


class ErrorHandler:
    """Utility class for standardized error handling in agent communication.
    
    This class provides methods for handling different types of errors,
    logging them appropriately, and generating error messages.
    
    Attributes:
        max_retries: Default maximum number of retries for operations
        retry_delay: Default delay between retries in seconds
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the error handler.
        
        Args:
            max_retries: Default maximum number of retries for operations
            retry_delay: Default delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def log_error(self, error: AgenticKernelError | Exception, context: dict[str, Any] | None = None):
        """Log an error with the appropriate severity level.
        
        Args:
            error: The error to log
            context: Optional context information about the error
        """
        context_str = f" Context: {context}" if context else ""
        
        if isinstance(error, AgenticKernelError):
            # Use the severity level from the error
            if error.severity == ErrorSeverity.DEBUG:
                logger.debug(f"{error.message}{context_str}")
            elif error.severity == ErrorSeverity.INFO:
                logger.info(f"{error.message}{context_str}")
            elif error.severity == ErrorSeverity.WARNING:
                logger.warning(f"{error.message}{context_str}")
            elif error.severity == ErrorSeverity.ERROR:
                logger.error(f"{error.message}{context_str}")
            elif error.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"{error.message}{context_str}")
        else:
            # Default to error level for standard exceptions
            logger.error(f"{str(error)}{context_str}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def format_error_message(
        self, 
        error: AgenticKernelError | Exception, 
        include_recovery: bool = True,
        include_stack_trace: bool = False,
    ) -> dict[str, Any]:
        """Format an error as a message for agent communication.
        
        Args:
            error: The error to format
            include_recovery: Whether to include recovery hints
            include_stack_trace: Whether to include the stack trace
            
        Returns:
            Dictionary containing formatted error information
        """
        if isinstance(error, AgenticKernelError):
            error_dict = error.to_dict()
            
            # Add stack trace if requested
            if include_stack_trace:
                error_dict["stack_trace"] = traceback.format_exc()
                
            # Remove recovery hints if not requested
            if not include_recovery:
                error_dict.pop("recovery_hints", None)
                
            return error_dict
        # Format standard exceptions
        error_dict = {
            "message": str(error),
            "code": error.__class__.__name__,
            "severity": "error",
            "category": "system",
            "details": {},
        }

        if include_stack_trace:
            error_dict["stack_trace"] = traceback.format_exc()

        return error_dict
    
    def generate_recovery_hints(self, error: AgenticKernelError | Exception) -> list[str]:
        """Generate recovery hints for an error.
        
        Args:
            error: The error to generate recovery hints for
            
        Returns:
            List of recovery hint strings
        """
        if isinstance(error, AgenticKernelError) and error.recovery_hints:
            return error.recovery_hints
        
        # Generate generic recovery hints based on error type
        if isinstance(error, MessageDeliveryError):
            return [
                "Check if the recipient agent is active and registered",
                "Verify network connectivity between agents",
                "Try again after a short delay",
            ]
        if isinstance(error, MessageTimeoutError):
            return [
                "Increase the timeout duration",
                "Check if the recipient agent is overloaded",
                "Try again with a simpler request",
            ]
        if isinstance(error, MessageValidationError):
            return [
                "Check the message format and content",
                "Verify that all required fields are present",
                "Ensure the message adheres to the protocol specification",
            ]
        if isinstance(error, ProtocolError):
            return [
                "Verify that both agents are using compatible protocol versions",
                "Check for protocol configuration issues",
                "Restart the communication channel",
            ]
        if isinstance(error, CommunicationError):
            return [
                "Check agent connectivity",
                "Verify message format",
                "Try again after a short delay",
            ]
        return [
            "Check system logs for more details",
            "Verify system configuration",
            "Contact system administrator if the issue persists",
        ]
    
    async def with_retries(
        self,
        operation: Callable[[], Any],
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_exceptions: list[type[Exception]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an operation with automatic retries on failure.
        
        Args:
            operation: The operation to execute
            max_retries: Maximum number of retries (defaults to self.max_retries)
            retry_delay: Delay between retries in seconds (defaults to self.retry_delay)
            retry_exceptions: List of exception types to retry on (defaults to CommunicationError)
            context: Optional context information for error logging
            
        Returns:
            The result of the operation
            
        Raises:
            The last exception encountered if all retries fail
        """
        max_retries = max_retries if max_retries is not None else self.max_retries
        retry_delay = retry_delay if retry_delay is not None else self.retry_delay
        retry_exceptions = retry_exceptions or [CommunicationError]
        
        retries = 0
        last_error = None
        
        while retries <= max_retries:
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation()
                return operation()
            except tuple(retry_exceptions) as e:
                last_error = e
                
                # Check if retry is possible for this error
                retry_possible = True
                if isinstance(e, AgenticKernelError):
                    retry_possible = e.retry_possible
                
                if not retry_possible or retries >= max_retries:
                    self.log_error(e, context)
                    raise
                
                retries += 1
                wait_time = retry_delay * (2 ** (retries - 1))  # Exponential backoff
                
                self.log_error(
                    e, 
                    {**(context or {}), "retry_count": retries, "next_retry_in": wait_time},
                )
                
                await asyncio.sleep(wait_time)
            except Exception as e:
                # Don't retry other exceptions
                self.log_error(e, context)
                raise
        
        # This should never happen, but just in case
        if last_error:
            raise last_error
        
        raise RuntimeError("Retry loop exited without result or exception")
    
    def validate_message(
        self, 
        message: dict[str, Any], 
        required_fields: list[str],
        field_types: dict[str, type] | None = None,
    ) -> None:
        """Validate a message against required fields and types.
        
        Args:
            message: The message to validate
            required_fields: List of required field names
            field_types: Optional mapping of field names to expected types
            
        Raises:
            MessageValidationError: If validation fails
        """
        # Check required fields
        missing_fields = [field for field in required_fields if field not in message]
        if missing_fields:
            raise MessageValidationError(
                f"Message missing required fields: {', '.join(missing_fields)}",
                details={"missing_fields": missing_fields, "message": message},
                recovery_hints=[
                    f"Ensure the message includes all required fields: {', '.join(required_fields)}",
                    "Check the message format specification",
                ],
            )
        
        # Check field types if provided
        if field_types:
            type_errors = []
            for field, expected_type in field_types.items():
                if field in message and not isinstance(message[field], expected_type):
                    type_errors.append(
                        f"{field} (expected {expected_type.__name__}, got {type(message[field]).__name__})",
                    )
            
            if type_errors:
                raise MessageValidationError(
                    f"Message contains fields with incorrect types: {', '.join(type_errors)}",
                    details={"type_errors": type_errors, "message": message},
                    recovery_hints=[
                        "Ensure all fields have the correct data types",
                        "Check the message format specification",
                    ],
                )