"""
Tests for the MockAgent class.

This module contains tests that demonstrate how to use the MockAgent class for testing
agent communication patterns in the Agentic Kernel system.
"""

import asyncio
import unittest

from src.agentic_kernel.communication.message import Message, MessageType
from src.agentic_kernel.communication.protocol import MessageBus
from src.agentic_kernel.types import Task
from tests.mock_agent import MockAgent


class TestMockAgent(unittest.IsolatedAsyncioTestCase):
    """
    Tests for the MockAgent class.
    """

    async def asyncSetUp(self):
        """
        Set up the test environment.
        """
        self.message_bus = MessageBus()
        self.message_bus.start()

        # Create two mock agents for testing communication
        self.agent1 = MockAgent(
            agent_id="agent1",
            message_bus=self.message_bus,
            capabilities={"task_execution": True, "query_handling": True},
        )

        self.agent2 = MockAgent(
            agent_id="agent2",
            message_bus=self.message_bus,
            capabilities={"task_execution": True, "query_handling": False},
        )

    async def asyncTearDown(self):
        """
        Clean up after the test.
        """
        self.message_bus.stop()

    async def test_execute_task(self):
        """
        Test that the mock agent can execute a task.
        """
        task = Task(
            task_id="test_task",
            description="Test task",
            agent_id="agent1",
            parameters={"param1": "value1"},
        )

        result = await self.agent1.execute(task)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "Mock execution of task: Test task")

    async def test_handle_query(self):
        """
        Test that the mock agent can handle a query.
        """
        query = "What is the meaning of life?"
        context = {"context_key": "context_value"}

        result = await self.agent1.handle_query(query, context)

        self.assertEqual(result["response"], "Mock response to query: What is the meaning of life?")
        self.assertEqual(result["confidence"], 0.9)

    async def test_agent_communication(self):
        """
        Test communication between two mock agents.
        """
        # Agent1 sends a task request to Agent2
        await self.agent1.request_task(
            recipient_id="agent2",
            task_description="Test task from agent1 to agent2",
            parameters={"param1": "value1"},
        )

        # Check that Agent2 received the task request
        messages = self.agent2.get_received_messages(MessageType.TASK_REQUEST)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "agent1")
        self.assertEqual(messages[0].receiver, "agent2")
        self.assertEqual(messages[0].content["description"], "Test task from agent1 to agent2")

        # Agent2 sends a query to Agent1
        await self.agent2.query_agent(
            recipient_id="agent1",
            query="Test query from agent2 to agent1",
            context={"context_key": "context_value"},
        )

        # Check that Agent1 received the query
        messages = self.agent1.get_received_messages(MessageType.QUERY)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "agent2")
        self.assertEqual(messages[0].receiver, "agent1")
        self.assertEqual(messages[0].content["query"], "Test query from agent2 to agent1")

    async def test_custom_response_handler(self):
        """
        Test setting a custom response handler for a specific message type.
        """
        # Create a custom handler for task requests
        custom_handler_called = False

        async def custom_task_handler(message: Message):
            nonlocal custom_handler_called
            custom_handler_called = True
            # Process the message in a custom way
            self.assertEqual(message.message_type, MessageType.TASK_REQUEST)
            self.assertEqual(message.content["description"], "Test task with custom handler")

        # Set the custom handler for Agent2
        self.agent2.set_response_handler(MessageType.TASK_REQUEST, custom_task_handler)

        # Agent1 sends a task request to Agent2
        await self.agent1.request_task(
            recipient_id="agent2",
            task_description="Test task with custom handler",
            parameters={"param1": "value1"},
        )

        # Wait a bit for the message to be processed
        await asyncio.sleep(0.1)

        # Check that the custom handler was called
        self.assertTrue(custom_handler_called)

    async def test_message_history(self):
        """
        Test recording and retrieving message history.
        """
        # Clear any existing messages
        self.agent1.clear_message_history()
        self.agent2.clear_message_history()

        # Agent1 sends a task request to Agent2
        await self.agent1.request_task(
            recipient_id="agent2",
            task_description="Test task for history",
            parameters={"param1": "value1"},
        )

        # Agent2 sends a status update to Agent1
        await self.agent2.send_status_update(
            recipient_id="agent1",
            status="processing",
            details={"progress": 50},
        )

        # Check Agent1's sent messages
        sent_messages = self.agent1.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0].message_type, MessageType.TASK_REQUEST)

        # Check Agent1's received messages
        received_messages = self.agent1.get_received_messages()
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].message_type, MessageType.STATUS_UPDATE)

        # Check Agent2's sent messages
        sent_messages = self.agent2.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0].message_type, MessageType.STATUS_UPDATE)

        # Check Agent2's received messages
        received_messages = self.agent2.get_received_messages()
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].message_type, MessageType.TASK_REQUEST)

        # Clear message history
        self.agent1.clear_message_history()
        self.agent2.clear_message_history()

        # Check that the message history is empty
        self.assertEqual(len(self.agent1.get_sent_messages()), 0)
        self.assertEqual(len(self.agent1.get_received_messages()), 0)
        self.assertEqual(len(self.agent2.get_sent_messages()), 0)
        self.assertEqual(len(self.agent2.get_received_messages()), 0)


if __name__ == "__main__":
    unittest.main()