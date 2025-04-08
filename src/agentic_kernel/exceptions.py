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


class AgenticKernelError(Exception):
    """Base exception class for all Agentic-Kernel errors.

    This class serves as the parent for all custom exceptions in the system.
    It provides a consistent interface and helps with error categorization.

    Attributes:
        message (str): Human-readable error description
        code (Optional[str]): Error code for programmatic handling
    """

    def __init__(self, message: str, code: str = None) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error description
            code: Optional error code for programmatic handling
        """
        self.message = message
        self.code = code
        super().__init__(self.message)


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

    def __init__(self, message: str, code: str = "TASK_NOT_FOUND") -> None:
        """Initialize the exception.

        Args:
            message: Description of which task was not found and why
            code: Error code, defaults to "TASK_NOT_FOUND"
        """
        super().__init__(message, code)


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

    def __init__(self, message: str, code: str = "TASK_EXECUTION_ERROR") -> None:
        """Initialize the exception.

        Args:
            message: Description of what went wrong during execution
            code: Error code, defaults to "TASK_EXECUTION_ERROR"
        """
        super().__init__(message, code)


class AgentError(AgenticKernelError):
    """Raised for errors related to agent operations (e.g., registration, configuration)."""
    def __init__(self, message: str, code: str = "AGENT_ERROR") -> None:
        super().__init__(message, code)


class SystemError(AgenticKernelError):
    """Raised for general system-level errors (e.g., configuration, initialization)."""
    def __init__(self, message: str, code: str = "SYSTEM_ERROR") -> None:
        super().__init__(message, code)
