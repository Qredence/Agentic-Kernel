"""Test script to demonstrate the A2A-compatible plugin system.

This script demonstrates how the A2A-compatible plugin system works by:
1. Creating a simple plugin that implements the enhanced BasePlugin class
2. Registering the plugin with the PluginRegistry
3. Showing how the plugin's capabilities are advertised through the A2A capability registry
4. Demonstrating how agents can discover and use the plugin's capabilities
"""

import asyncio
import logging
import sys

# Add the src directory to the Python path
sys.path.append("src")

from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.communication.capability_registry import CapabilityRegistry
from agentic_kernel.communication.message import Message, MessageType
from agentic_kernel.communication.protocol import CommunicationProtocol, MessageBus
from agentic_kernel.plugins.base import BasePlugin
from agentic_kernel.plugins.registry import PluginRegistry

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SimpleCalculatorPlugin(BasePlugin):
    """A simple calculator plugin for demonstration purposes."""
    
    def __init__(self, config: dict | None = None):
        """Initialize the calculator plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(
            name="simple_calculator",
            description="A simple calculator plugin for basic arithmetic operations",
            config=config,
            version="1.0.0",
        )
        
        # Set A2A capability types
        self.set_a2a_capability_types({"problem_solving", "reasoning"})
    
    def get_capabilities(self) -> dict[str, str]:
        """Get the capabilities of this plugin.
        
        Returns:
            Dictionary mapping capability names to descriptions
        """
        return {
            "add": "Add two numbers together",
            "subtract": "Subtract one number from another",
            "multiply": "Multiply two numbers together",
            "divide": "Divide one number by another",
        }
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum of the two numbers
        """
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract one number from another.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Difference between the two numbers
        """
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product of the two numbers
        """
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide one number by another.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Quotient of the two numbers
            
        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b


class CalculatorAgent(BaseAgent):
    """An agent that uses the calculator plugin."""
    
    def __init__(self, agent_id: str):
        """Initialize the calculator agent.
        
        Args:
            agent_id: ID of the agent
        """
        self.agent_id = agent_id
        self.message_bus = MessageBus()
        self.protocol = CommunicationProtocol(agent_id, self.message_bus)
        self.capability_registry = CapabilityRegistry(self.protocol)
        self.plugin_registry = PluginRegistry(self.capability_registry)
        
        # Register message handlers
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """Set up message handlers for different message types."""
        self.protocol.register_handler(
            MessageType.CAPABILITY_REQUEST, self._handle_capability_request,
        )
        self.protocol.register_handler(
            MessageType.TASK_REQUEST, self._handle_task_request,
        )
    
    async def _handle_capability_request(self, message: Message):
        """Handle a capability request message."""
        logger.info(f"Agent {self.agent_id} received capability request from {message.sender}")
        await self.capability_registry.handle_capability_request_message(message)
    
    async def _handle_task_request(self, message: Message):
        """Handle a task request message."""
        logger.info(f"Agent {self.agent_id} received task request from {message.sender}")
        
        content = message.content
        task_description = content.get("task_description", "")
        parameters = content.get("parameters", {})
        
        # Check if this is a calculator task
        if "calculate" in task_description.lower():
            # Extract operation and numbers from parameters
            operation = parameters.get("operation")
            a = parameters.get("a")
            b = parameters.get("b")
            
            if not operation or a is None or b is None:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="invalid_parameters",
                    description="Missing required parameters: operation, a, b",
                    correlation_id=message.message_id,
                )
                return
            
            # Get the calculator plugin
            calculator_plugin = await self.plugin_registry.get_plugin("simple_calculator")
            if not calculator_plugin:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="plugin_not_found",
                    description="Calculator plugin not found",
                    correlation_id=message.message_id,
                )
                return
            
            # Perform the calculation
            try:
                result = None
                if operation == "add":
                    result = calculator_plugin.add(a, b)
                elif operation == "subtract":
                    result = calculator_plugin.subtract(a, b)
                elif operation == "multiply":
                    result = calculator_plugin.multiply(a, b)
                elif operation == "divide":
                    result = calculator_plugin.divide(a, b)
                else:
                    await self.protocol.send_error(
                        recipient=message.sender,
                        error_type="invalid_operation",
                        description=f"Unsupported operation: {operation}",
                        correlation_id=message.message_id,
                    )
                    return
                
                # Send the result
                await self.protocol.send_task_response(
                    request_id=message.message_id,
                    recipient=message.sender,
                    status="completed",
                    result={"value": result},
                )
            
            except Exception as e:
                await self.protocol.send_error(
                    recipient=message.sender,
                    error_type="calculation_error",
                    description=str(e),
                    correlation_id=message.message_id,
                )
        else:
            await self.protocol.send_error(
                recipient=message.sender,
                error_type="unsupported_task",
                description="This agent only supports calculator tasks",
                correlation_id=message.message_id,
            )


class UserAgent(BaseAgent):
    """A simple agent that represents a user interacting with the system."""
    
    def __init__(self, agent_id: str):
        """Initialize the user agent.
        
        Args:
            agent_id: ID of the agent
        """
        self.agent_id = agent_id
        self.message_bus = MessageBus()
        self.protocol = CommunicationProtocol(agent_id, self.message_bus)
        self.capability_registry = CapabilityRegistry(self.protocol)
        
        # Register message handlers
        self._setup_message_handlers()
    
    def _setup_message_handlers(self):
        """Set up message handlers for different message types."""
        self.protocol.register_handler(
            MessageType.CAPABILITY_RESPONSE, self._handle_capability_response,
        )
        self.protocol.register_handler(
            MessageType.TASK_RESPONSE, self._handle_task_response,
        )
        self.protocol.register_handler(
            MessageType.ERROR, self._handle_error,
        )
    
    async def _handle_capability_response(self, message: Message):
        """Handle a capability response message."""
        logger.info(f"Agent {self.agent_id} received capability response from {message.sender}")
        capabilities = message.content.get("capabilities", [])
        logger.info(f"Available capabilities: {capabilities}")
    
    async def _handle_task_response(self, message: Message):
        """Handle a task response message."""
        logger.info(f"Agent {self.agent_id} received task response from {message.sender}")
        status = message.content.get("status")
        result = message.content.get("result")
        logger.info(f"Task status: {status}, result: {result}")
    
    async def _handle_error(self, message: Message):
        """Handle an error message."""
        logger.info(f"Agent {self.agent_id} received error from {message.sender}")
        error_type = message.content.get("error_type")
        description = message.content.get("description")
        logger.error(f"Error: {error_type} - {description}")
    
    async def request_capabilities(self, recipient: str):
        """Request capabilities from another agent.
        
        Args:
            recipient: ID of the agent to request capabilities from
        """
        logger.info(f"Agent {self.agent_id} requesting capabilities from {recipient}")
        await self.capability_registry.request_agent_capabilities(
            recipient=recipient,
            detail_level="full",
        )
    
    async def request_calculation(self, recipient: str, operation: str, a: float, b: float):
        """Request a calculation from another agent.
        
        Args:
            recipient: ID of the agent to request the calculation from
            operation: The operation to perform (add, subtract, multiply, divide)
            a: First number
            b: Second number
        """
        logger.info(f"Agent {self.agent_id} requesting calculation from {recipient}")
        await self.protocol.request_task(
            recipient=recipient,
            task_description=f"Calculate {a} {operation} {b}",
            parameters={
                "operation": operation,
                "a": a,
                "b": b,
            },
        )


async def main():
    """Run the A2A plugin system demonstration."""
    # Create the calculator agent
    calculator_agent = CalculatorAgent("calculator_agent")
    
    # Create the user agent
    user_agent = UserAgent("user_agent")
    
    # Create and register the calculator plugin
    plugin = SimpleCalculatorPlugin()
    await calculator_agent.plugin_registry.register(SimpleCalculatorPlugin)
    
    # Wait for plugin registration to complete
    await asyncio.sleep(1)
    
    # User agent requests capabilities from calculator agent
    await user_agent.request_capabilities("calculator_agent")
    
    # Wait for capability response
    await asyncio.sleep(1)
    
    # User agent requests calculations from calculator agent
    await user_agent.request_calculation("calculator_agent", "add", 5, 3)
    await user_agent.request_calculation("calculator_agent", "subtract", 10, 4)
    await user_agent.request_calculation("calculator_agent", "multiply", 6, 7)
    await user_agent.request_calculation("calculator_agent", "divide", 20, 5)
    
    # Try a division by zero to test error handling
    await user_agent.request_calculation("calculator_agent", "divide", 10, 0)
    
    # Wait for all responses
    await asyncio.sleep(2)
    
    logger.info("A2A plugin system demonstration completed")


if __name__ == "__main__":
    asyncio.run(main())