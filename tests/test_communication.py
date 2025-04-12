"""Tests for the agent communication protocol implementation."""

import pytest
import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import uuid

from agentic_kernel.communication.protocol import MessageBus, CommunicationProtocol
from agentic_kernel.communication.message import (
    MessageType,
    Message,
    MessagePriority,
    TaskResponse,
    QueryResponse,
    ErrorMessage,
    AgentDiscoveryMessage,
    ConsensusRequestMessage,
    ConsensusVoteMessage,
    ConsensusResultMessage,
    ConflictNotificationMessage,
    ConflictResolutionMessage,
    FeedbackMessage,
    CoordinationRequestMessage,
    CoordinationResponseMessage,
    TaskDecompositionMessage
)
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.config import AgentConfig
from agentic_kernel.types import Task


class TestAgent(BaseAgent):
    """Test agent implementation."""

    def __init__(self, config: AgentConfig, message_bus: MessageBus):
        super().__init__(config, message_bus)
        self.received_responses: Dict[str, Message] = {}
        self.received_query_responses: Dict[str, Message] = {}
        self.response_events: Dict[str, asyncio.Event] = {}
        self.processed_message_contents: List[Dict[str, Any]] = []

    async def _handle_message(self, message: Message):
        """Generic message handler to record processing order."""
        self.processed_message_contents.append(message.content)

        handler = self.protocol.handlers.get(message.message_type)
        if handler:
            await handler(message)
        else:
            pass

    async def _handle_task_request(self, message: Message):
        """Handle task requests and log processing order."""
        self.processed_message_contents.append(message.content)
        await super()._handle_task_request(message)

    async def _handle_task_response(self, message: Message):
        """Handle incoming task responses."""
        self.processed_message_contents.append(message.content)
        if message.correlation_id:
            self.received_responses[message.correlation_id] = message
            if event := self.response_events.get(message.correlation_id):
                event.set()

    async def _handle_query_request(self, message: Message):
        """Handle query requests and log processing order."""
        self.processed_message_contents.append(message.content)
        await super()._handle_query_request(message)

    async def _handle_query_response(self, message: Message):
        """Handle incoming query responses."""
        self.processed_message_contents.append(message.content)
        if message.correlation_id:
            self.received_query_responses[message.correlation_id] = message
            if event := self.response_events.get(message.correlation_id):
                event.set()

    async def handle_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Any:
        await asyncio.sleep(0.01)
        if query == "test query":
            return {"result": "test_result_from_handler"}
        else:
            raise NotImplementedError(f"Query '{query}' not handled by TestAgent")

    async def execute(self, task: Task) -> Dict[str, Any]:
        await asyncio.sleep(0.01)
        return {
            "status": "completed",
            "output": {"message": f"Task {task.description} executed"}
        }

    def _get_supported_tasks(self) -> Dict[str, Any]:
        return {
            "test_task": {
                "description": "Test task",
                "parameters": ["param1"]
            }
        }


@pytest.fixture
async def message_bus():
    """Create a message bus instance for testing."""
    bus = MessageBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
def agent_config():
    """Create an agent configuration for testing."""
    return AgentConfig(
        name="test_agent",
        description="Test agent",
        parameters={}
    )


@pytest.fixture
async def test_agent(message_bus, agent_config):
    """Create a test agent instance."""
    agent = TestAgent(agent_config, message_bus)
    yield agent


@pytest.mark.asyncio
async def test_message_bus_start_stop(message_bus):
    """Test starting and stopping the message bus."""
    assert message_bus.is_running()
    await message_bus.stop()
    assert not message_bus.is_running()


@pytest.mark.asyncio
async def test_protocol_message_handling(message_bus, test_agent):
    """Test basic message handling through the protocol."""
    # Create mock handler
    mock_handler = AsyncMock()
    test_agent.protocol.register_handler(MessageType.TASK_REQUEST, mock_handler)

    # Send test message
    message = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task_description": "test", "parameters": {}},
        sender="test_sender",
        recipient=test_agent.agent_id
    )

    await message_bus.publish(message)

    # Wait for message processing
    await asyncio.sleep(0.1)

    # Verify handler was called
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args.message_type == MessageType.TASK_REQUEST
    assert call_args.content["task_description"] == "test"


@pytest.mark.asyncio
async def test_task_request_response(message_bus, test_agent):
    """Test task request and response flow, verifying response reception."""
    # Create another agent to send the request
    requester_config = AgentConfig(name="requester", description="", parameters={})
    requester = TestAgent(requester_config, message_bus)

    # Prepare to wait for the response
    request_id = str(uuid.uuid4())
    response_event = asyncio.Event()
    requester.response_events[request_id] = response_event

    # Send task request using the protocol directly to set correlation_id easily
    await requester.protocol.send_message(
        recipient=test_agent.agent_id,
        message_type=MessageType.TASK_REQUEST,
        content={"task_description": "Execute test task", "parameters": {"param1": "value1"}},
        correlation_id=request_id
    )

    # Wait for the response event to be set, with a timeout
    try:
        await asyncio.wait_for(response_event.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Timed out waiting for task response")

    # Verify task response was received by the requester
    assert request_id in requester.received_responses
    response_message = requester.received_responses[request_id]
    assert isinstance(response_message, TaskResponse)
    assert response_message.message_type == MessageType.TASK_RESPONSE
    assert response_message.content["status"] == "completed"
    assert "Task Execute test task executed" in response_message.content["output"]["message"]
    assert response_message.sender == test_agent.agent_id
    assert response_message.recipient == requester.agent_id


@pytest.mark.asyncio
async def test_query_response(message_bus, test_agent):
    """Test query and response flow, verifying response reception."""
    # Create another agent to send the query
    requester_config = AgentConfig(name="query_requester", description="", parameters={})
    requester = TestAgent(requester_config, message_bus)

    # Prepare to wait for the response
    query_id = str(uuid.uuid4())
    response_event = asyncio.Event()
    requester.response_events[query_id] = response_event

    # Send query using the protocol directly
    await requester.protocol.query_agent(
        recipient_id=test_agent.agent_id,
        query="test query",
        context={"key": "value"},
        correlation_id=query_id
    )

    # Wait for the response event to be set, with a timeout
    try:
        await asyncio.wait_for(response_event.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Timed out waiting for query response")

    # Verify query response was received by the requester
    assert query_id in requester.received_query_responses
    response_message = requester.received_query_responses[query_id]

    # Add specific assertions for QueryResponse if the type hint is available
    assert response_message.message_type == MessageType.QUERY_RESPONSE
    assert response_message.content["result"] == {"result": "test_result_from_handler"}
    assert response_message.sender == test_agent.agent_id
    assert response_message.recipient == requester.agent_id
    assert response_message.correlation_id == query_id


@pytest.mark.asyncio
async def test_capability_request(message_bus, test_agent):
    """Test capability request and response."""
    # Create another agent to request capabilities
    requester = TestAgent(AgentConfig(name="requester", description="", parameters={}), message_bus)

    # Create mock handler for capability response
    mock_handler = AsyncMock()
    requester.protocol.register_handler(MessageType.CAPABILITY_RESPONSE, mock_handler)

    # Send capability request
    await requester.protocol.send_message(
        recipient=test_agent.agent_id,
        message_type=MessageType.CAPABILITY_REQUEST,
        content={}
    )

    # Wait for response
    await asyncio.sleep(0.1)

    # Verify response was received
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args.message_type == MessageType.CAPABILITY_RESPONSE
    assert "test_task" in call_args.content["capabilities"]


@pytest.mark.asyncio
async def test_status_updates(message_bus, test_agent):
    """Test sending and receiving status updates."""
    # Create another agent to receive updates
    receiver = TestAgent(AgentConfig(name="receiver", description="", parameters={}), message_bus)

    # Create mock handler for status updates
    mock_handler = AsyncMock()
    receiver.protocol.register_handler(MessageType.STATUS_UPDATE, mock_handler)

    # Send status update
    await test_agent.send_status_update(
        recipient_id=receiver.agent_id,
        status="test_status",
        details={"key": "value"}
    )

    # Wait for update processing
    await asyncio.sleep(0.1)

    # Verify update was received
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args.message_type == MessageType.STATUS_UPDATE
    assert call_args.content["status"] == "test_status"
    assert call_args.content["details"]["key"] == "value"


@pytest.mark.asyncio
async def test_error_handling(message_bus, test_agent):
    """Test error handling in communication."""
    # Create another agent to receive errors
    receiver = TestAgent(AgentConfig(name="receiver", description="", parameters={}), message_bus)

    # Create mock handler for errors
    mock_handler = AsyncMock()
    receiver.protocol.register_handler(MessageType.ERROR, mock_handler)

    # Trigger an error by sending an invalid task request
    await test_agent.protocol.send_task_response(
        request_id="invalid_id",
        recipient=receiver.agent_id,
        status="failed",
        error="Test error"
    )

    # Wait for error processing
    await asyncio.sleep(0.1)

    # Verify error was handled
    mock_handler.assert_called_once()
    call_args = mock_handler.call_args[0][0]
    assert call_args.message_type == MessageType.ERROR


@pytest.mark.asyncio
async def test_message_priorities(message_bus, test_agent):
    """Test message priority handling ensures high priority messages are processed first."""
    test_agent.processed_message_contents.clear()

    high_priority = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task_description": "high", "parameters": {}},
        sender="test_sender",
        recipient=test_agent.agent_id,
        priority=MessagePriority.HIGH
    )

    low_priority = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task_description": "low", "parameters": {}},
        sender="test_sender",
        recipient=test_agent.agent_id,
        priority=MessagePriority.LOW
    )

    await message_bus.publish(low_priority)
    await message_bus.publish(high_priority)

    await asyncio.sleep(0.2)

    assert len(test_agent.processed_message_contents) >= 2, \
        f"Expected at least 2 messages processed, got {len(test_agent.processed_message_contents)}"

    processed_descriptions = [msg_content.get("task_description") for msg_content in test_agent.processed_message_contents]

    try:
        high_index = processed_descriptions.index("high")
    except ValueError:
        pytest.fail("High priority message content not found in processed messages")

    try:
        low_index = processed_descriptions.index("low")
    except ValueError:
        pytest.fail("Low priority message content not found in processed messages")

    assert high_index < low_index, \
        f"High priority message (index {high_index}) was not processed before low priority message (index {low_index})\nProcessed order: {processed_descriptions}"


@pytest.mark.asyncio
async def test_message_routing(message_bus, test_agent):
    """Test message routing between multiple agents."""
    # Create additional test agents
    agent2 = TestAgent(AgentConfig(name="agent2", description="", parameters={}), message_bus)
    agent3 = TestAgent(AgentConfig(name="agent3", description="", parameters={}), message_bus)

    # Send messages between agents
    message1 = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "test1"},
        sender=test_agent.agent_id,
        recipient=agent2.agent_id
    )
    message2 = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "test2"},
        sender=agent2.agent_id,
        recipient=agent3.agent_id
    )

    await message_bus.publish(message1)
    await message_bus.publish(message2)

    await asyncio.sleep(0.1)

    # Verify messages were routed correctly
    assert {"task": "test1"} in agent2.processed_message_contents
    assert {"task": "test2"} in agent3.processed_message_contents
    assert {"task": "test2"} not in test_agent.processed_message_contents


@pytest.mark.asyncio
async def test_message_filtering(message_bus, test_agent):
    """Test message filtering based on recipient and message type."""
    # Create a second agent
    agent2 = TestAgent(AgentConfig(name="agent2", description="", parameters={}), message_bus)

    # Register specific message type handler
    mock_handler = AsyncMock()
    test_agent.protocol.register_handler(MessageType.QUERY_REQUEST, mock_handler)

    # Send different message types
    messages = [
        Message(
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test1"},
            sender=agent2.agent_id,
            recipient=test_agent.agent_id
        ),
        Message(
            message_type=MessageType.QUERY_REQUEST,
            content={"query": "test2"},
            sender=agent2.agent_id,
            recipient=test_agent.agent_id
        ),
        Message(
            message_type=MessageType.QUERY_REQUEST,
            content={"query": "test3"},
            sender=agent2.agent_id,
            recipient=agent2.agent_id  # Different recipient
        )
    ]

    for message in messages:
        await message_bus.publish(message)

    await asyncio.sleep(0.1)

    # Verify only relevant messages were handled
    assert mock_handler.call_count == 1
    call_args = mock_handler.call_args[0][0]
    assert call_args.content["query"] == "test2"


@pytest.mark.asyncio
async def test_agent_discovery(message_bus, test_agent):
    """Test agent discovery and registration process."""
    # Create agents with specific capabilities
    agent2 = TestAgent(
        AgentConfig(
            name="specialized_agent",
            description="Agent with specific capabilities",
            parameters={"capabilities": ["special_task"]}
        ),
        message_bus
    )

    # Send discovery request
    discovery_msg = AgentDiscoveryMessage(
        sender=test_agent.agent_id,
        recipient="broadcast",
        content={"required_capabilities": ["special_task"]}
    )

    # Prepare to collect responses
    discovery_responses = []

    async def collect_response(msg):
        if isinstance(msg, AgentDiscoveryMessage) and msg.sender != test_agent.agent_id:
            discovery_responses.append(msg)

    test_agent.protocol.register_handler(
        MessageType.AGENT_DISCOVERY,
        collect_response
    )

    await message_bus.publish(discovery_msg)
    await asyncio.sleep(0.1)

    # Verify discovery results
    assert len(discovery_responses) == 1
    response = discovery_responses[0]
    assert response.sender == agent2.agent_id
    assert "special_task" in response.content["capabilities"]


@pytest.mark.asyncio
async def test_priority_based_routing(message_bus, test_agent):
    """Test that high-priority messages are processed before low-priority ones."""
    # Create messages with different priorities
    low_priority = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "low_priority"},
        sender="sender",
        recipient=test_agent.agent_id,
        priority=MessagePriority.LOW
    )

    high_priority = Message(
        message_type=MessageType.TASK_REQUEST,
        content={"task": "high_priority"},
        sender="sender",
        recipient=test_agent.agent_id,
        priority=MessagePriority.HIGH
    )

    # Send low priority first, then high priority
    await message_bus.publish(low_priority)
    await message_bus.publish(high_priority)

    await asyncio.sleep(0.1)

    # Verify processing order
    assert len(test_agent.processed_message_contents) == 2
    assert test_agent.processed_message_contents[0]["task"] == "high_priority"
    assert test_agent.processed_message_contents[1]["task"] == "low_priority" 


@pytest.mark.asyncio
async def test_consensus_building(message_bus, test_agent):
    """Test consensus building process with request, vote, and result."""
    # Create multiple agents to participate in consensus
    agent1 = TestAgent(AgentConfig(name="agent1", description="", parameters={}), message_bus)
    agent2 = TestAgent(AgentConfig(name="agent2", description="", parameters={}), message_bus)
    agent3 = TestAgent(AgentConfig(name="agent3", description="", parameters={}), message_bus)

    # Create mock handlers for consensus messages
    consensus_request_handler = AsyncMock()
    consensus_vote_handler = AsyncMock()
    consensus_result_handler = AsyncMock()

    # Register handlers for all agents
    for agent in [agent1, agent2, agent3]:
        agent.protocol.register_handler(MessageType.CONSENSUS_REQUEST, consensus_request_handler)
        agent.protocol.register_handler(MessageType.CONSENSUS_VOTE, consensus_vote_handler)
        agent.protocol.register_handler(MessageType.CONSENSUS_RESULT, consensus_result_handler)

    # Request consensus
    recipients = [agent1.agent_id, agent2.agent_id, agent3.agent_id]
    topic = "test_decision"
    options = ["option1", "option2", "option3"]
    context = {"key": "value"}

    message_ids = await test_agent.protocol.request_consensus(
        recipients=recipients,
        topic=topic,
        options=options,
        context=context,
        voting_mechanism="majority"
    )

    # Wait for request processing
    await asyncio.sleep(0.1)

    # Verify consensus requests were received
    assert consensus_request_handler.call_count == 3
    for call_args in consensus_request_handler.call_args_list:
        message = call_args[0][0]
        assert message.message_type == MessageType.CONSENSUS_REQUEST
        assert message.content["topic"] == topic
        assert message.content["options"] == options
        assert message.content["context"] == context
        assert message.content["voting_mechanism"] == "majority"

    # Send votes from each agent
    consensus_id = "test_consensus_id"
    for agent, option in zip([agent1, agent2, agent3], ["option1", "option2", "option1"]):
        await agent.protocol.send_consensus_vote(
            request_id=message_ids[agent.agent_id],
            recipient=test_agent.agent_id,
            consensus_id=consensus_id,
            vote=option,
            confidence=0.8,
            rationale="Test rationale"
        )

    # Wait for vote processing
    await asyncio.sleep(0.1)

    # Verify votes were received
    assert consensus_vote_handler.call_count == 3
    for call_args in consensus_vote_handler.call_args_list:
        message = call_args[0][0]
        assert message.message_type == MessageType.CONSENSUS_VOTE
        assert message.content["consensus_id"] == consensus_id
        assert message.content["vote"] in options
        assert message.content["confidence"] == 0.8
        assert message.content["rationale"] == "Test rationale"

    # Send consensus result
    vote_distribution = {
        "option1": 2,
        "option2": 1,
        "option3": 0
    }

    await test_agent.protocol.send_consensus_result(
        recipients=recipients,
        consensus_id=consensus_id,
        result="option1",
        vote_distribution=vote_distribution,
        confidence=0.9,
        next_steps=["proceed with option1"]
    )

    # Wait for result processing
    await asyncio.sleep(0.1)

    # Verify results were received
    assert consensus_result_handler.call_count == 3
    for call_args in consensus_result_handler.call_args_list:
        message = call_args[0][0]
        assert message.message_type == MessageType.CONSENSUS_RESULT
        assert message.content["consensus_id"] == consensus_id
        assert message.content["result"] == "option1"
        assert message.content["vote_distribution"] == vote_distribution
        assert message.content["confidence"] == 0.9
        assert message.content["next_steps"] == ["proceed with option1"]


@pytest.mark.asyncio
async def test_conflict_resolution(message_bus, test_agent):
    """Test conflict notification and resolution process."""
    # Create multiple agents to participate in conflict resolution
    agent1 = TestAgent(AgentConfig(name="agent1", description="", parameters={}), message_bus)
    agent2 = TestAgent(AgentConfig(name="agent2", description="", parameters={}), message_bus)

    # Create mock handlers for conflict messages
    conflict_notification_handler = AsyncMock()
    conflict_resolution_handler = AsyncMock()

    # Register handlers for all agents
    for agent in [agent1, agent2]:
        agent.protocol.register_handler(MessageType.CONFLICT_NOTIFICATION, conflict_notification_handler)
        agent.protocol.register_handler(MessageType.CONFLICT_RESOLUTION, conflict_resolution_handler)

    # Notify about a conflict
    recipients = [agent1.agent_id, agent2.agent_id]
    conflict_type = "resource_allocation"
    description = "Conflicting resource requests"
    parties = [agent1.agent_id, agent2.agent_id]
    impact = {"severity": "medium", "affected_tasks": ["task1", "task2"]}

    message_ids = await test_agent.protocol.notify_conflict(
        recipients=recipients,
        conflict_type=conflict_type,
        description=description,
        parties=parties,
        impact=impact
    )

    # Wait for notification processing
    await asyncio.sleep(0.1)

    # Verify conflict notifications were received
    assert conflict_notification_handler.call_count == 2
    for call_args in conflict_notification_handler.call_args_list:
        message = call_args[0][0]
        assert message.message_type == MessageType.CONFLICT_NOTIFICATION
        assert message.content["conflict_type"] == conflict_type
        assert message.content["description"] == description
        assert message.content["parties"] == parties
        assert message.content["impact"] == impact

    # Send conflict resolution
    conflict_id = "test_conflict_id"
    resolution = "time_sharing"
    rationale = "Allocate resources in alternating time slots"
    required_actions = {
        agent1.agent_id: ["adjust schedule", "reduce resource usage"],
        agent2.agent_id: ["delay start", "use alternative resource"]
    }
    verification_method = "monitor resource usage"

    await test_agent.protocol.send_conflict_resolution(
        recipients=recipients,
        conflict_id=conflict_id,
        resolution=resolution,
        rationale=rationale,
        required_actions=required_actions,
        verification_method=verification_method
    )

    # Wait for resolution processing
    await asyncio.sleep(0.1)

    # Verify conflict resolutions were received
    assert conflict_resolution_handler.call_count == 2
    for call_args in conflict_resolution_handler.call_args_list:
        message = call_args[0][0]
        assert message.message_type == MessageType.CONFLICT_RESOLUTION
        assert message.content["conflict_id"] == conflict_id
        assert message.content["resolution"] == resolution
        assert message.content["rationale"] == rationale
        assert message.content["required_actions"] == required_actions
        assert message.content["verification_method"] == verification_method


@pytest.mark.asyncio
async def test_feedback(message_bus, test_agent):
    """Test sending and receiving feedback."""
    # Create an agent to receive feedback
    receiver = TestAgent(AgentConfig(name="receiver", description="", parameters={}), message_bus)

    # Create mock handler for feedback
    feedback_handler = AsyncMock()
    receiver.protocol.register_handler(MessageType.FEEDBACK, feedback_handler)

    # Send feedback
    feedback_type = "performance"
    rating = 4.5
    description = "Good performance on task execution"
    improvement_suggestions = ["Improve response time", "Add more detailed explanations"]
    context = {"task_id": "task123", "domain": "data_processing"}

    await test_agent.protocol.send_feedback(
        recipient=receiver.agent_id,
        feedback_type=feedback_type,
        rating=rating,
        description=description,
        improvement_suggestions=improvement_suggestions,
        context=context
    )

    # Wait for feedback processing
    await asyncio.sleep(0.1)

    # Verify feedback was received
    feedback_handler.assert_called_once()
    message = feedback_handler.call_args[0][0]
    assert message.message_type == MessageType.FEEDBACK
    assert message.content["feedback_type"] == feedback_type
    assert message.content["rating"] == rating
    assert message.content["description"] == description
    assert message.content["improvement_suggestions"] == improvement_suggestions
    assert message.content["context"] == context


@pytest.mark.asyncio
async def test_coordination(message_bus, test_agent):
    """Test coordination request and response flow."""
    # Create an agent to coordinate with
    coordinator = TestAgent(AgentConfig(name="coordinator", description="", parameters={}), message_bus)

    # Create mock handlers for coordination messages
    coordination_request_handler = AsyncMock()
    coordination_response_handler = AsyncMock()

    # Register handlers
    coordinator.protocol.register_handler(MessageType.COORDINATION_REQUEST, coordination_request_handler)
    test_agent.protocol.register_handler(MessageType.COORDINATION_RESPONSE, coordination_response_handler)

    # Prepare coordination request
    coordination_type = "resource_scheduling"
    activities = [
        {"id": "activity1", "name": "Data processing", "duration": 30},
        {"id": "activity2", "name": "Model training", "duration": 60}
    ]
    constraints = {"max_duration": 120, "priority": "high"}
    dependencies = {"activity2": ["activity1"]}

    # Send coordination request
    request_id = await test_agent.protocol.request_coordination(
        recipient=coordinator.agent_id,
        coordination_type=coordination_type,
        activities=activities,
        constraints=constraints,
        dependencies=dependencies,
        priority=MessagePriority.HIGH
    )

    # Wait for request processing
    await asyncio.sleep(0.1)

    # Verify coordination request was received
    coordination_request_handler.assert_called_once()
    request_message = coordination_request_handler.call_args[0][0]
    assert request_message.message_type == MessageType.COORDINATION_REQUEST
    assert request_message.content["coordination_type"] == coordination_type
    assert request_message.content["activities"] == activities
    assert request_message.content["constraints"] == constraints
    assert request_message.content["dependencies"] == dependencies
    assert request_message.priority == MessagePriority.HIGH

    # Send coordination response
    coordination_id = "coord123"
    response = "accept"
    availability = {"start_time": "2023-01-01T10:00:00Z", "end_time": "2023-01-01T14:00:00Z"}
    conditions = {"resource_limit": 80}
    proposed_schedule = {
        "activity1": {"start": "2023-01-01T10:00:00Z", "end": "2023-01-01T10:30:00Z"},
        "activity2": {"start": "2023-01-01T10:30:00Z", "end": "2023-01-01T11:30:00Z"}
    }

    await coordinator.protocol.send_coordination_response(
        request_id=request_id,
        recipient=test_agent.agent_id,
        coordination_id=coordination_id,
        response=response,
        availability=availability,
        conditions=conditions,
        proposed_schedule=proposed_schedule
    )

    # Wait for response processing
    await asyncio.sleep(0.1)

    # Verify coordination response was received
    coordination_response_handler.assert_called_once()
    response_message = coordination_response_handler.call_args[0][0]
    assert response_message.message_type == MessageType.COORDINATION_RESPONSE
    assert response_message.content["coordination_id"] == coordination_id
    assert response_message.content["response"] == response
    assert response_message.content["availability"] == availability
    assert response_message.content["conditions"] == conditions
    assert response_message.content["proposed_schedule"] == proposed_schedule
    assert response_message.correlation_id == request_id


@pytest.mark.asyncio
async def test_task_decomposition(message_bus, test_agent):
    """Test sending and receiving task decomposition."""
    # Create an agent to receive task decomposition
    receiver = TestAgent(AgentConfig(name="receiver", description="", parameters={}), message_bus)

    # Create mock handler for task decomposition
    task_decomposition_handler = AsyncMock()
    receiver.protocol.register_handler(MessageType.TASK_DECOMPOSITION, task_decomposition_handler)

    # Prepare task decomposition data
    parent_task_id = "parent_task_123"
    subtasks = [
        {
            "id": "subtask1",
            "name": "Data collection",
            "description": "Collect data from sources",
            "agent_type": "data_collector",
            "parameters": {"source": "database"}
        },
        {
            "id": "subtask2",
            "name": "Data processing",
            "description": "Process collected data",
            "agent_type": "data_processor",
            "parameters": {"format": "json"}
        },
        {
            "id": "subtask3",
            "name": "Report generation",
            "description": "Generate report from processed data",
            "agent_type": "report_generator",
            "parameters": {"template": "standard"}
        }
    ]
    dependencies = {
        "subtask2": ["subtask1"],
        "subtask3": ["subtask2"]
    }
    allocation_suggestions = {
        "data_collector_agent": ["subtask1"],
        "data_processor_agent": ["subtask2"],
        "report_generator_agent": ["subtask3"]
    }
    estimated_complexity = {
        "subtask1": 0.3,
        "subtask2": 0.5,
        "subtask3": 0.2
    }

    # Send task decomposition
    await test_agent.protocol.send_task_decomposition(
        recipient=receiver.agent_id,
        parent_task_id=parent_task_id,
        subtasks=subtasks,
        dependencies=dependencies,
        allocation_suggestions=allocation_suggestions,
        estimated_complexity=estimated_complexity
    )

    # Wait for decomposition processing
    await asyncio.sleep(0.1)

    # Verify task decomposition was received
    task_decomposition_handler.assert_called_once()
    message = task_decomposition_handler.call_args[0][0]
    assert message.message_type == MessageType.TASK_DECOMPOSITION
    assert message.content["parent_task_id"] == parent_task_id
    assert message.content["subtasks"] == subtasks
    assert message.content["dependencies"] == dependencies
    assert message.content["allocation_suggestions"] == allocation_suggestions
    assert message.content["estimated_complexity"] == estimated_complexity
