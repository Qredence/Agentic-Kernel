"""Base agent class for the Agentic-Kernel system.

This module defines the base agent class that all specialized agents must inherit from.
It provides the core interface and common functionality for agent implementations.

Key features:
1. Task execution interface
2. Task validation
3. Pre/post processing hooks
4. Capability reporting
5. Configuration management
6. Inter-agent communication

Example:

    .. code-block:: python

        class MyAgent(BaseAgent):
            async def execute(self, task: Task) -> Dict[str, Any]:
                # Custom task execution logic
                result = await process_task(task)
                return {"status": "success", "data": result}
                
            def _get_supported_tasks(self) -> Dict[str, Any]:
                return {
                    "my_task_type": {
                        "description": "Handles specific task type",
                        "parameters": ["param1", "param2"]
                    }
                }
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypedDict

from ..communication.message import Message, MessageType
from ..communication.protocol import CommunicationProtocol, MessageBus
from ..config import AgentConfig
from ..types import Task

logger = logging.getLogger(__name__)


class TaskCapability(TypedDict):
    """Type definition for task capability information.

    This type defines the structure of capability information for a single
    task type that an agent can handle.

    Attributes:
        description (str): Human-readable description of the task type.
        parameters (List[str]): List of required parameters for the task.
        optional_parameters (Optional[List[str]]): List of optional parameters.
        examples (Optional[List[Dict[str, Any]]]): List of example task configurations.
    """

    description: str
    parameters: List[str]
    optional_parameters: Optional[List[str]]
    examples: Optional[List[Dict[str, Any]]]


class AgentCapabilities(TypedDict):
    """Type definition for agent capabilities.

    This type defines the structure of an agent's complete capability report.

    Attributes:
        type (str): The type identifier for this agent.
        supported_tasks (Dict[str, TaskCapability]): Dictionary mapping task types to their capabilities.
        config (Dict[str, Any]): The agent's current configuration.
    """

    type: str
    supported_tasks: Dict[str, TaskCapability]
    config: Dict[str, Any]


class BaseAgent(ABC):
    """Base class for all agents in the system.

    This abstract class defines the interface that all agents must implement.
    It provides common functionality and hooks for task execution, validation,
    capability reporting, and inter-agent communication.

    The agent lifecycle typically follows these steps:
    1. Task validation
    2. Task preprocessing
    3. Task execution
    4. Result postprocessing

    Attributes:
        config (AgentConfig): Configuration parameters for the agent.
        type (str): The agent's type identifier, derived from class name.
        agent_id (str): Unique identifier for this agent instance.
        protocol (CommunicationProtocol): Protocol for inter-agent communication.

    Example:
        .. code-block:: python 

            class DataProcessor(BaseAgent):
                async def execute(self, task: Task) -> Dict[str, Any]:
                    data = await process_data(task.parameters["input"])
                    return {"processed_data": data}
    
                def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
                    return {
                        "process_data": {
                            "description": "Process input data",
                            "parameters": ["input"],
                            "optional_parameters": ["format"],
                            "examples": [
                                {"input": "data.csv", "format": "csv"}
                            ]
                        }
                    }
    """

    def __init__(
        self, config: AgentConfig, message_bus: Optional[MessageBus] = None
    ) -> None:
        """Initialize the base agent.

        Args:
            config (AgentConfig): Configuration parameters for the agent.
            message_bus (Optional[MessageBus]): Optional message bus for communication.
        """
        self.config = config
        self.type = self.__class__.__name__.lower().replace("agent", "")
        self.agent_id = str(uuid.uuid4())

        # Setup communication protocol if message bus provided
        self.protocol = None
        if message_bus:
            self.protocol = CommunicationProtocol(self.agent_id, message_bus)
            self._setup_message_handlers()

    def _setup_message_handlers(self):
        """Setup handlers for different message types."""
        if not self.protocol:
            return

        # Register task request handler
        self.protocol.register_handler(
            MessageType.TASK_REQUEST, self._handle_task_request
        )

        # Register query handler
        self.protocol.register_handler(MessageType.QUERY, self._handle_query)

        # Register capability request handler
        self.protocol.register_handler(
            MessageType.CAPABILITY_REQUEST, self._handle_capability_request
        )

    async def _handle_task_request(self, message: Message):
        """Handle incoming task requests.

        Args:
            message (Message): The task request message.
        """
        try:
            # Extract task details
            task = Task(
                description=message.content["task_description"],
                parameters=message.content["parameters"],
                agent_type=self.type,
            )

            # Execute task
            result = await self.execute(task)

            # Send response
            if self.protocol:
                await self.protocol.send_task_response(
                    request_id=message.message_id,
                    recipient=message.sender,
                    status=result.get("status", "completed"),
                    result=result.get("output"),
                    error=result.get("error"),
                    metrics=result.get("metrics"),
                )

        except Exception as e:
            logger.error(f"Error handling task request: {str(e)}")
            if self.protocol:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="task_execution_failed",
                    description=str(e),
                )

    async def _handle_query(self, message: Message):
        """Handle incoming queries.

        Args:
            message (Message): The query message.
        """
        try:
            # Process query
            query = message.content["query"]
            context = message.content.get("context", {})
            required_format = message.content.get("required_format")

            # Get query result
            result = await self.handle_query(query, context)

            # Send response
            if self.protocol:
                await self.protocol.send_query_response(
                    query_id=message.message_id, recipient=message.sender, result=result
                )

        except Exception as e:
            logger.error(f"Error handling query: {str(e)}")
            if self.protocol:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="query_failed",
                    description=str(e),
                )

    async def _handle_capability_request(self, message: Message):
        """Handle capability requests.

        Args:
            message (Message): The capability request message.
        """
        try:
            capabilities = self._get_supported_tasks()

            if self.protocol:
                await self.protocol.send_message(
                    recipient=message.sender,
                    message_type=MessageType.CAPABILITY_RESPONSE,
                    content={"capabilities": capabilities},
                    correlation_id=message.message_id,
                )

        except Exception as e:
            logger.error(f"Error handling capability request: {str(e)}")
            if self.protocol:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="capability_request_failed",
                    description=str(e),
                )

    async def handle_query(self, query: str, context: Dict[str, Any]) -> Any:
        """Handle an information query.

        This method should be overridden by agents that support querying.

        Args:
            query (str): The query string.
            context (Dict[str, Any]): Additional context for the query.

        Returns:
            Any: Query result.

        Raises:
            NotImplementedError: If agent doesn't support queries.
        """
        raise NotImplementedError("This agent does not support queries")

    @abstractmethod
    async def execute(self, task: Task) -> Dict[str, Any]:
        """Execute a task.

        This is the main method that must be implemented by all agent classes.
        It should contain the core logic for handling tasks of the agent's type.

        Args:
            task (Task): The task to execute, containing all necessary information.

        Returns:
            Dict[str, Any]: Dictionary containing the task execution results. The structure
            depends on the specific agent implementation, but should typically include:

            - status: The final task status
            - output: The task's output data
            - metrics: Any relevant execution metrics

        Raises:
            TaskExecutionError: If task execution fails.

        Example:
            .. code-block:: python

                async def execute(self, task: Task) -> Dict[str, Any]:
                    try:
                        result = await self._process_task(task)
                        return {
                            "status": "completed",
                            "output": result,
                            "metrics": {"duration": 1.5}
                        }
                    except Exception as e:
                        raise TaskExecutionError(str(e))
        """
        pass

    @abstractmethod
    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        """Get the tasks supported by this agent.

        Returns:
            Dict[str, TaskCapability]: Dictionary mapping task types to their capabilities.

        Example:
            .. code-block:: python

                capabilities = agent._get_supported_tasks()
                print(capabilities['chat']['description'])
        """
        pass

    async def request_task(
        self, recipient_id: str, task_description: str, parameters: Dict[str, Any]
    ) -> str:
        """Request another agent to perform a task.

        Args:
            recipient_id (str): ID of the agent to perform the task.
            task_description (str): Description of the task.
            parameters (Dict[str, Any]): Task parameters.

        Returns:
            str: The message ID of the task request.

        Raises:
            RuntimeError: If communication protocol not initialized.
        """
        if not self.protocol:
            raise RuntimeError("Communication protocol not initialized")

        return await self.protocol.request_task(
            recipient=recipient_id,
            task_description=task_description,
            parameters=parameters,
        )

    async def query_agent(
        self, recipient_id: str, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Query another agent for information.

        Args:
            recipient_id (str): ID of the agent to query.
            query (str): The query string.
            context (Optional[Dict[str, Any]]): Optional context information.

        Returns:
            str: The message ID of the query.

        Raises:
            RuntimeError: If communication protocol not initialized.
        """
        if not self.protocol:
            raise RuntimeError("Communication protocol not initialized")

        return await self.protocol.query_agent(
            recipient=recipient_id, query=query, context=context
        )

    async def send_status_update(
        self, recipient_id: str, status: str, details: Optional[Dict[str, Any]] = None
    ):
        """Send a status update to another agent.

        Args:
            recipient_id (str): ID of the receiving agent.
            status (str): Current status.
            details (Optional[Dict[str, Any]]): Optional status details.

        Raises:
            RuntimeError: If communication protocol not initialized.
        """
        if not self.protocol:
            raise RuntimeError("Communication protocol not initialized")

        await self.protocol.send_status_update(
            recipient=recipient_id, status=status, details=details
        )

    async def validate_task(self, task: Task) -> bool:
        """Validate if the agent can handle the given task.

        This method checks if the task is appropriate for this agent by
        verifying the task type and any required parameters.

        Args:
            task (Task): The task to validate.

        Returns:
            bool: True if the agent can handle the task, False otherwise.

        Example:
            .. code-block:: python

                # Override in subclass for custom validation
                async def validate_task(self, task: Task) -> bool:
                    if not await super().validate_task(task):
                        return False

                    # Additional validation logic
                    required_params = ["input_file"]
                    return all(p in task.parameters for p in required_params)
        """
        return task.agent_type == self.type

    async def preprocess_task(self, task: Task) -> Task:
        """Preprocess a task before execution.

        This hook allows agents to modify or enhance tasks before execution.
        Common uses include parameter validation, value normalization, and
        adding default values.

        Args:
            task (Task): The task to preprocess.

        Returns:
            Task: The preprocessed task.

        Example:
            .. code-block:: python

                async def preprocess_task(self, task: Task) -> Task:
                    # Add default parameters
                    task.parameters.setdefault("format", "json")

                    # Normalize paths
                    if "input_path" in task.parameters:
                        task.parameters["input_path"] = os.path.abspath(
                            task.parameters["input_path"]
                        )

                    return task
        """
        return task

    async def postprocess_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Postprocess the task execution result.

        This hook allows agents to modify or enhance the execution result
        before it's returned to the caller. Common uses include data
        formatting, adding metadata, and cleanup.

        Args:
            result (Dict[str, Any]): The raw execution result.

        Returns:
            Dict[str, Any]: The postprocessed result.

        Example:
            .. code-block:: python

                async def postprocess_result(
                    self,
                    result: Dict[str, Any]
                ) -> Dict[str, Any]:
                    # Add execution timestamp
                    result["timestamp"] = datetime.now().isoformat()

                    # Format output data
                    if "data" in result:
                        result["data"] = self._format_data(result["data"])

                    return result
        """
        return result

    def get_capabilities(self) -> AgentCapabilities:
        """Get the agent's capabilities.

        This method returns a structured description of the agent's capabilities,
        including its type, supported tasks, and current configuration.

        Returns:
            AgentCapabilities: A dictionary describing the agent's complete capabilities.

        Example:
            .. code-block:: python

                capabilities = agent.get_capabilities()
                print(f"Agent type: {capabilities['type']}")
                for task_type, details in capabilities['supported_tasks'].items():
                    print(f"- {task_type}: {details['description']}")
        """
        return {
            "type": self.type,
            "supported_tasks": self._get_supported_tasks(),
            "config": self.config.dict(),
        }
