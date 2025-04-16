"""
Message handling functionality for agents.

This module contains classes and methods for handling different types of
messages between agents, including task requests, queries, and capability
requests.
"""

from typing import Any

from ...communication.message import Message, MessageType
from ...types import Task
from .base_agent import BaseAgent


class MessageHandlingMixin:
    """
    Mixin class providing message handling functionality for agents.
    
    This mixin provides methods for handling different types of messages
    and for sending messages to other agents.
    """
    
    def _handle_task_request(self, message: Message) -> None:
        """
        Handle a task request message.
        
        Args:
            message: The task request message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        self.logger.info(f"Received task request from {message.sender_id}")
        
        try:
            # Extract task from message
            task_data = message.content.get("task", {})
            task = Task(
                task_id=task_data.get("task_id", ""),
                task_type=task_data.get("task_type", ""),
                description=task_data.get("description", ""),
                parameters=task_data.get("parameters", {}),
                deadline=task_data.get("deadline"),
                priority=task_data.get("priority", 0),
            )
            
            # Execute the task
            result = self.execute(task)
            
            # Send response
            response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.TASK_RESPONSE,
                content={
                    "task_id": task.task_id,
                    "result": result,
                    "status": "completed",
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(response)
            
        except Exception as e:
            # Send error response
            error_response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.TASK_RESPONSE,
                content={
                    "task_id": task_data.get("task_id", ""),
                    "result": None,
                    "status": "error",
                    "error": str(e),
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(error_response)
            self.logger.error(f"Error handling task request: {str(e)}")

    def _handle_query(self, message: Message) -> None:
        """
        Handle a query message.
        
        Args:
            message: The query message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        self.logger.info(f"Received query from {message.sender_id}")
        
        try:
            # Extract query from message
            query = message.content.get("query", "")
            context = message.content.get("context", {})
            
            # Handle the query
            result = self.handle_query(query, context)
            
            # Send response
            response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.QUERY_RESPONSE,
                content={
                    "result": result,
                    "status": "completed",
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(response)
            
        except Exception as e:
            # Send error response
            error_response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.QUERY_RESPONSE,
                content={
                    "result": None,
                    "status": "error",
                    "error": str(e),
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(error_response)
            self.logger.error(f"Error handling query: {str(e)}")

    def _handle_capability_request(self, message: Message) -> None:
        """
        Handle a capability request message.
        
        Args:
            message: The capability request message
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        self.logger.info(f"Received capability request from {message.sender_id}")
        
        try:
            # Get agent capabilities
            capabilities = self.get_capabilities()
            
            # Send response
            response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.CAPABILITY_RESPONSE,
                content={
                    "capabilities": capabilities,
                    "status": "completed",
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(response)
            
        except Exception as e:
            # Send error response
            error_response = self.protocol.create_message(
                sender_id=self.id,
                recipient_id=message.sender_id,
                message_type=MessageType.CAPABILITY_RESPONSE,
                content={
                    "capabilities": None,
                    "status": "error",
                    "error": str(e),
                },
                reference_message_id=message.message_id,
            )
            
            self.message_bus.send_message(error_response)
            self.logger.error(f"Error handling capability request: {str(e)}")

    def request_task(self, recipient_id: str, task_description: str, parameters: dict[str, Any]) -> str:
        """
        Send a task request to another agent.
        
        Args:
            recipient_id: ID of the recipient agent
            task_description: Description of the task
            parameters: Parameters for the task
            
        Returns:
            The message ID of the request
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        task_id = f"task_{self.id}_{recipient_id}_{len(self.execution_times)}"
        
        # Create task request message
        message = self.protocol.create_message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=MessageType.TASK_REQUEST,
            content={
                "task": {
                    "task_id": task_id,
                    "task_type": "custom",  # Can be customized based on task
                    "description": task_description,
                    "parameters": parameters,
                },
            },
        )
        
        # Send the message
        self.message_bus.send_message(message)
        self.logger.info(f"Sent task request to {recipient_id}")
        
        return message.message_id

    def query_agent(self, recipient_id: str, query: str, context: dict[str, Any] | None = None) -> str:
        """
        Send a query to another agent.
        
        Args:
            recipient_id: ID of the recipient agent
            query: The query string
            context: Optional context for the query
            
        Returns:
            The message ID of the query
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        # Create query message
        message = self.protocol.create_message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=MessageType.QUERY,
            content={
                "query": query,
                "context": context or {},
            },
        )
        
        # Send the message
        self.message_bus.send_message(message)
        self.logger.info(f"Sent query to {recipient_id}")
        
        return message.message_id

    def send_status_update(self, recipient_id: str, status: str, details: dict[str, Any] | None = None) -> str:
        """
        Send a status update to another agent.
        
        Args:
            recipient_id: ID of the recipient agent
            status: Status string
            details: Optional details about the status
            
        Returns:
            The message ID of the status update
        """
        if not isinstance(self, BaseAgent):
            raise TypeError("MessageHandlingMixin must be used with BaseAgent")
            
        if not self.message_bus:
            raise ValueError("Message bus is required for agent communication")
            
        # Create status update message
        message = self.protocol.create_message(
            sender_id=self.id,
            recipient_id=recipient_id,
            message_type=MessageType.STATUS_UPDATE,
            content={
                "status": status,
                "details": details or {},
                "timestamp": self.protocol.get_timestamp(),
            },
        )
        
        # Send the message
        self.message_bus.send_message(message)
        self.logger.info(f"Sent status update to {recipient_id}")
        
        return message.message_id