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
    AgentRegistrationMessage
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
        if isinstance(msg, AgentRegistrationMessage):
            discovery_responses.append(msg)
    
    test_agent.protocol.register_handler(
        MessageType.AGENT_REGISTRATION,
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