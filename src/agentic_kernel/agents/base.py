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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

from ..communication.collaborative_protocol import CollaborativeProtocol
from ..communication.feedback import (
    FeedbackCategory,
    FeedbackEntry,
    FeedbackManager,
    FeedbackSeverity,
    LearningStrategy,
)
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
        self.collaborative_protocol = None
        self.feedback_manager = None

        # Initialize agent parameters with defaults
        self.parameters = {
            # Performance parameters
            "response_time_target": 1.0,  # Target response time in seconds
            "max_tokens_per_response": 1000,  # Maximum tokens per response

            # Quality parameters
            "quality_threshold": 0.7,  # Minimum quality threshold (0.0-1.0)
            "review_frequency": 0.2,  # Frequency of response review (0.0-1.0)

            # Accuracy parameters
            "fact_checking_enabled": False,  # Whether fact checking is enabled
            "confidence_threshold": 0.8,  # Minimum confidence threshold (0.0-1.0)

            # Communication parameters
            "verbosity": 0.5,  # Verbosity level (0.0-1.0)
            "formality": 0.5,  # Formality level (0.0-1.0)
        }

        # Override defaults with any parameters from config
        if hasattr(config, "parameters") and config.parameters:
            for key, value in config.parameters.items():
                if key in self.parameters:
                    self.parameters[key] = value

        if message_bus:
            self.protocol = CommunicationProtocol(self.agent_id, message_bus)
            self.collaborative_protocol = CollaborativeProtocol(self.protocol)
            self.feedback_manager = FeedbackManager(
                learning_strategy=LearningStrategy.ADAPTIVE
            )
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

        # Register consensus-related handlers
        self.protocol.register_handler(
            MessageType.CONSENSUS_REQUEST, self._handle_consensus_request
        )
        self.protocol.register_handler(
            MessageType.CONSENSUS_VOTE, self._handle_consensus_vote
        )
        self.protocol.register_handler(
            MessageType.CONSENSUS_RESULT, self._handle_consensus_result
        )

        # Register feedback handler
        self.protocol.register_handler(
            MessageType.FEEDBACK, self._handle_feedback
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

    # Consensus-related methods

    async def _handle_consensus_request(self, message: Message):
        """Handle incoming consensus request messages.

        Args:
            message (Message): The consensus request message.
        """
        if not self.collaborative_protocol:
            logger.error("Cannot handle consensus request: collaborative protocol not initialized")
            return

        try:
            # Extract consensus information
            consensus_id = message.content.get("consensus_id")
            topic = message.content.get("topic")
            options = message.content.get("options", [])

            # Default implementation: vote for the first option with neutral confidence
            if options:
                vote = options[0]
                confidence = 0.5
                rationale = f"Default vote from {self.agent_id}"

                # Send vote back to requester
                await self.protocol.send_consensus_vote(
                    request_id=message.message_id,
                    recipient=message.sender,
                    consensus_id=consensus_id,
                    vote=vote,
                    confidence=confidence,
                    rationale=rationale
                )
            else:
                logger.warning(f"Received consensus request with no options: {consensus_id}")
        except Exception as e:
            logger.error(f"Error handling consensus request: {str(e)}")

    async def _handle_consensus_vote(self, message: Message):
        """Handle incoming consensus vote messages.

        Args:
            message (Message): The consensus vote message.
        """
        if not self.collaborative_protocol:
            logger.error("Cannot handle consensus vote: collaborative protocol not initialized")
            return

        try:
            # Extract vote information
            consensus_id = message.content.get("consensus_id")
            vote = message.content.get("vote")
            confidence = message.content.get("confidence", 1.0)
            rationale = message.content.get("rationale")

            # Process the vote
            await self.collaborative_protocol.process_consensus_vote(
                message_id=message.message_id,
                sender=message.sender,
                consensus_id=consensus_id,
                vote=vote,
                confidence=confidence,
                rationale=rationale
            )
        except Exception as e:
            logger.error(f"Error handling consensus vote: {str(e)}")

    async def _handle_consensus_result(self, message: Message):
        """Handle incoming consensus result messages.

        Args:
            message (Message): The consensus result message.
        """
        # Default implementation: log the result
        try:
            consensus_id = message.content.get("consensus_id")
            result = message.content.get("result")
            confidence = message.content.get("confidence")

            logger.info(f"Received consensus result for {consensus_id}: {result} (confidence: {confidence})")
        except Exception as e:
            logger.error(f"Error handling consensus result: {str(e)}")

    async def request_consensus(
        self,
        recipients: List[str],
        topic: str,
        options: List[Any],
        context: Optional[Dict[str, Any]] = None,
        voting_mechanism: str = "majority",
        min_participants: int = 1,
        voting_deadline: Optional[datetime] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Request consensus from multiple agents.

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

        Raises:
            RuntimeError: If collaborative protocol is not initialized
        """
        if not self.collaborative_protocol:
            raise RuntimeError("Cannot request consensus: collaborative protocol not initialized")

        return await self.collaborative_protocol.create_consensus_process(
            recipients=recipients,
            topic=topic,
            options=options,
            context=context or {},
            voting_mechanism=voting_mechanism,
            min_participants=min_participants,
            voting_deadline=voting_deadline,
        )

    async def send_consensus_vote(
        self,
        request_id: str,
        recipient: str,
        consensus_id: str,
        vote: Any,
        confidence: float = 1.0,
        rationale: Optional[str] = None,
    ):
        """Send a vote in a consensus process.

        Args:
            request_id: ID of the original consensus request
            recipient: ID of the agent that requested consensus
            consensus_id: ID of the consensus request
            vote: The agent's vote
            confidence: Confidence level in the vote (0.0-1.0)
            rationale: Explanation for the vote

        Raises:
            RuntimeError: If protocol is not initialized
        """
        if not self.protocol:
            raise RuntimeError("Cannot send consensus vote: protocol not initialized")

        await self.protocol.send_consensus_vote(
            request_id=request_id,
            recipient=recipient,
            consensus_id=consensus_id,
            vote=vote,
            confidence=confidence,
            rationale=rationale,
        )

    async def check_consensus_status(
        self, consensus_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if consensus has been reached.

        Args:
            consensus_id: ID of the consensus process

        Returns:
            Tuple containing:
            - Boolean indicating if consensus is complete
            - Result dictionary if complete, None otherwise

        Raises:
            RuntimeError: If collaborative protocol is not initialized
        """
        if not self.collaborative_protocol:
            raise RuntimeError("Cannot check consensus status: collaborative protocol not initialized")

        is_complete, result = await self.collaborative_protocol.check_consensus_status(consensus_id)

        if is_complete and result:
            return True, {
                "result": result.result,
                "vote_distribution": result.vote_distribution,
                "confidence": result.confidence,
                "participant_count": result.participant_count,
                "next_steps": result.next_steps,
            }

        return False, None

    # Feedback-related methods

    async def _handle_feedback(self, message: Message):
        """Handle incoming feedback messages.

        This method processes feedback received from other agents or users,
        analyzes it, and adjusts agent behavior accordingly.

        Args:
            message (Message): The feedback message.
        """
        if not self.feedback_manager:
            logger.error("Cannot handle feedback: feedback manager not initialized")
            return

        try:
            # Extract feedback details from the message
            feedback_type = message.content.get("feedback_type", "performance")
            rating = message.content.get("rating", 0.5)
            description = message.content.get("description", "")
            improvement_suggestions = message.content.get("improvement_suggestions", [])
            context = message.content.get("context", {})

            # Map feedback type to category
            try:
                category = FeedbackCategory(feedback_type)
            except ValueError:
                # Default to performance if category not recognized
                category = FeedbackCategory.PERFORMANCE

            # Determine severity based on rating
            if rating >= 0.8:
                severity = FeedbackSeverity.POSITIVE
            elif rating >= 0.6:
                severity = FeedbackSeverity.LOW
            elif rating >= 0.4:
                severity = FeedbackSeverity.MEDIUM
            elif rating >= 0.2:
                severity = FeedbackSeverity.HIGH
            else:
                severity = FeedbackSeverity.CRITICAL

            # Create feedback entry
            feedback = FeedbackEntry(
                agent_id=self.agent_id,
                source_id=message.sender,
                category=category,
                severity=severity,
                rating=rating,
                description=description,
                improvement_suggestions=improvement_suggestions,
                context=context,
                task_id=context.get("task_id"),
                conversation_id=message.conversation_id,
                metadata={"message_id": message.message_id}
            )

            # Process the feedback and update parameters
            await self.process_feedback(feedback)

            # Log feedback receipt
            logger.info(
                f"Received feedback from {message.sender}: {category.value} "
                f"(rating: {rating:.2f}, severity: {severity.value})"
            )

        except Exception as e:
            logger.error(f"Error handling feedback: {str(e)}")

    async def process_feedback(self, feedback: FeedbackEntry) -> Dict[str, Any]:
        """Process a feedback entry and update agent behavior.

        This method implements the feedback loop by:
        1. Storing the feedback
        2. Analyzing it to generate insights
        3. Generating adjustments based on the insights
        4. Applying the adjustments to agent parameters

        Args:
            feedback: The feedback entry to process

        Returns:
            Updated agent parameters
        """
        if not self.feedback_manager:
            logger.warning("Cannot process feedback: feedback manager not initialized")
            return self.parameters

        # Process feedback and update parameters
        _, _, updated_parameters = self.feedback_manager.process_feedback(
            feedback, self.parameters
        )

        # Update agent parameters
        self.parameters = updated_parameters

        # Log parameter changes
        logger.info(f"Updated agent parameters based on feedback: {self.parameters}")

        return self.parameters

    def get_performance_metrics(
        self,
        category: Optional[FeedbackCategory] = None,
        metric_name: Optional[str] = None,
        window_size: int = 10
    ) -> Dict[str, List[Tuple[datetime, float]]]:
        """Get performance metrics for this agent.

        Args:
            category: Optional category to filter by
            metric_name: Optional metric name to filter by
            window_size: Maximum number of metrics to return per name

        Returns:
            Dictionary mapping metric names to lists of (timestamp, value) tuples
        """
        if not self.feedback_manager:
            return {}

        # Get metrics from feedback manager
        metrics = self.feedback_manager.get_agent_performance(
            self.agent_id, category, metric_name
        )

        # Limit to the most recent metrics
        for name in metrics:
            metrics[name] = metrics[name][-window_size:]

        return metrics

    def get_performance_trend(
        self,
        metric_name: str,
        window_size: int = 5
    ) -> Optional[float]:
        """Get the trend for a specific performance metric.

        Args:
            metric_name: Name of the metric to analyze
            window_size: Number of most recent metrics to consider

        Returns:
            Float indicating the trend (positive = improving, negative = declining),
            or None if not enough data points
        """
        if not self.feedback_manager:
            return None

        return self.feedback_manager.get_performance_trend(
            self.agent_id, metric_name, window_size
        )

    def get_insights(
        self,
        category: Optional[FeedbackCategory] = None,
        min_confidence: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Get insights derived from feedback analysis.

        Args:
            category: Optional category to filter by
            min_confidence: Minimum confidence level for insights

        Returns:
            List of insight dictionaries
        """
        if not self.feedback_manager:
            return []

        # Get insights from feedback analyzer
        insights = self.feedback_manager.feedback_analyzer.get_agent_insights(
            self.agent_id, category, min_confidence
        )

        # Convert to dictionaries
        return [
            {
                "insight_id": insight.insight_id,
                "category": insight.category.value,
                "description": insight.description,
                "confidence": insight.confidence,
                "improvement_actions": insight.improvement_actions,
                "timestamp": insight.timestamp.isoformat(),
            }
            for insight in insights
        ]

    def get_adjustments(
        self,
        category: Optional[FeedbackCategory] = None,
        min_confidence: float = 0.6,
        applied_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get adjustments made to agent parameters.

        Args:
            category: Optional category to filter by
            min_confidence: Minimum confidence level for adjustments
            applied_only: Whether to only include applied adjustments

        Returns:
            List of adjustment dictionaries
        """
        if not self.feedback_manager:
            return []

        # Get adjustments from feedback learner
        adjustments = self.feedback_manager.feedback_learner.get_agent_adjustments(
            self.agent_id, category, min_confidence, applied_only
        )

        # Convert to dictionaries
        return [
            {
                "adjustment_id": adjustment.adjustment_id,
                "category": adjustment.category.value,
                "parameter": adjustment.parameter,
                "old_value": adjustment.old_value,
                "new_value": adjustment.new_value,
                "confidence": adjustment.confidence,
                "applied": adjustment.applied,
                "timestamp": adjustment.timestamp.isoformat(),
            }
            for adjustment in adjustments
        ]

    async def send_feedback(
        self,
        recipient_id: str,
        category: FeedbackCategory,
        rating: float,
        description: str,
        improvement_suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send feedback to another agent.

        Args:
            recipient_id: ID of the agent to receive feedback
            category: Category of the feedback
            rating: Numerical rating (0.0-1.0, higher is better)
            description: Detailed description of the feedback
            improvement_suggestions: Suggestions for improvement
            context: Context in which the feedback applies

        Returns:
            The message ID of the feedback message

        Raises:
            RuntimeError: If protocol is not initialized
        """
        if not self.protocol:
            raise RuntimeError("Cannot send feedback: protocol not initialized")

        return await self.protocol.send_feedback(
            recipient=recipient_id,
            feedback_type=category.value,
            rating=rating,
            description=description,
            improvement_suggestions=improvement_suggestions,
            context=context or {}
        )

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
