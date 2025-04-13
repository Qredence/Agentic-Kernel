"""Dynamic agent discovery and capability advertisement system.

This module extends the basic capability registry to provide dynamic agent discovery
and real-time capability advertisement. It enables agents to automatically discover
other agents in the system, subscribe to capability updates, and receive notifications
when new capabilities become available.

Key features:
1. Periodic capability broadcasting for automatic discovery
2. Capability subscription for real-time updates
3. Dynamic capability matching based on requirements
4. Capability versioning and update notification
5. Agent presence monitoring and health checks
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from .capability_registry import AgentCapability, AgentInfo, CapabilityRegistry
from .message import (
    AgentDiscoveryMessage,
)
from .protocol import CommunicationProtocol

logger = logging.getLogger(__name__)


class CapabilitySubscription:
    """Subscription to capability updates.
    
    This class represents a subscription to capability updates for specific
    capability types or from specific agents.
    
    Attributes:
        subscriber_id: ID of the subscribing agent
        capability_types: Types of capabilities to subscribe to
        agent_ids: IDs of agents to subscribe to
        callback: Function to call when a matching capability is updated
        expiration: When the subscription expires
        last_notified: When the subscriber was last notified
    """
    
    def __init__(
        self,
        subscriber_id: str,
        capability_types: list[str] | None = None,
        agent_ids: list[str] | None = None,
        callback: Callable[[AgentCapability, str], None] | None = None,
        expiration_minutes: int = 60,
    ):
        """Initialize a capability subscription.
        
        Args:
            subscriber_id: ID of the subscribing agent
            capability_types: Types of capabilities to subscribe to
            agent_ids: IDs of agents to subscribe to
            callback: Function to call when a matching capability is updated
            expiration_minutes: Minutes until the subscription expires
        """
        self.subscriber_id = subscriber_id
        self.capability_types = capability_types or []
        self.agent_ids = agent_ids or []
        self.callback = callback
        self.expiration = datetime.utcnow() + timedelta(minutes=expiration_minutes)
        self.last_notified = datetime.utcnow()
        
    def is_expired(self) -> bool:
        """Check if the subscription has expired.
        
        Returns:
            True if the subscription has expired, False otherwise
        """
        return datetime.utcnow() > self.expiration
    
    def matches(self, capability: AgentCapability, agent_id: str) -> bool:
        """Check if a capability matches this subscription.
        
        Args:
            capability: Capability to check
            agent_id: ID of the agent with the capability
            
        Returns:
            True if the capability matches the subscription, False otherwise
        """
        # If specific capability types are specified, check for a match
        if self.capability_types and capability.capability_type not in self.capability_types:
            return False
        
        # If specific agent IDs are specified, check for a match
        if self.agent_ids and agent_id not in self.agent_ids:
            return False
            
        return True
    
    def extend(self, minutes: int = 60) -> None:
        """Extend the subscription expiration.
        
        Args:
            minutes: Minutes to extend the subscription by
        """
        self.expiration = datetime.utcnow() + timedelta(minutes=minutes)


class AgentPresenceMonitor:
    """Monitor agent presence and health.
    
    This class monitors the presence and health of agents in the system,
    detecting when agents become unavailable or unresponsive.
    
    Attributes:
        agents: Dictionary mapping agent IDs to their last seen timestamps
        timeout_seconds: Seconds after which an agent is considered inactive
        callback: Function to call when an agent's status changes
    """
    
    def __init__(
        self,
        timeout_seconds: int = 300,
        callback: Callable[[str, str], None] | None = None,
    ):
        """Initialize an agent presence monitor.
        
        Args:
            timeout_seconds: Seconds after which an agent is considered inactive
            callback: Function to call when an agent's status changes
        """
        self.agents: dict[str, datetime] = {}
        self.timeout_seconds = timeout_seconds
        self.callback = callback
        self.agent_statuses: dict[str, str] = {}  # Maps agent IDs to their current status
        
    def update_agent_timestamp(self, agent_id: str) -> None:
        """Update the last seen timestamp for an agent.
        
        Args:
            agent_id: ID of the agent to update
        """
        self.agents[agent_id] = datetime.utcnow()
        
        # If the agent was previously inactive, mark it as active and notify
        if self.agent_statuses.get(agent_id) == "inactive":
            self.agent_statuses[agent_id] = "active"
            if self.callback:
                self.callback(agent_id, "active")
        else:
            self.agent_statuses[agent_id] = "active"
    
    def check_agent_timeouts(self) -> list[str]:
        """Check for agents that have timed out.
        
        Returns:
            List of agent IDs that have timed out
        """
        now = datetime.utcnow()
        timeout_threshold = now - timedelta(seconds=self.timeout_seconds)
        
        timed_out_agents = []
        for agent_id, last_seen in list(self.agents.items()):
            if last_seen < timeout_threshold:
                timed_out_agents.append(agent_id)
                
                # If the agent was previously active, mark it as inactive and notify
                if self.agent_statuses.get(agent_id) == "active":
                    self.agent_statuses[agent_id] = "inactive"
                    if self.callback:
                        self.callback(agent_id, "inactive")
        
        return timed_out_agents
    
    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from monitoring.
        
        Args:
            agent_id: ID of the agent to remove
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
        
        if agent_id in self.agent_statuses:
            del self.agent_statuses[agent_id]


class DynamicCapabilityRegistry(CapabilityRegistry):
    """Dynamic registry for agent capabilities and discovery.
    
    This class extends the basic capability registry to provide dynamic agent
    discovery and real-time capability advertisement.
    
    Attributes:
        subscriptions: List of capability subscriptions
        presence_monitor: Monitor for agent presence
        broadcast_interval: Seconds between automatic capability broadcasts
        discovery_task: Task for periodic discovery broadcasts
        presence_check_task: Task for periodic presence checks
    """
    
    def __init__(
        self,
        protocol: CommunicationProtocol | None = None,
        broadcast_interval: int = 300,
        presence_timeout: int = 600,
    ):
        """Initialize the dynamic capability registry.
        
        Args:
            protocol: Communication protocol for sending messages
            broadcast_interval: Seconds between automatic capability broadcasts
            presence_timeout: Seconds after which an agent is considered inactive
        """
        super().__init__(protocol)
        self.subscriptions: list[CapabilitySubscription] = []
        self.presence_monitor = AgentPresenceMonitor(
            timeout_seconds=presence_timeout,
            callback=self._handle_agent_status_change,
        )
        self.broadcast_interval = broadcast_interval
        self.discovery_task: asyncio.Task | None = None
        self.presence_check_task: asyncio.Task | None = None
        self.running = False
        
    async def start(self) -> None:
        """Start the dynamic capability registry.
        
        This method starts the periodic tasks for capability broadcasting
        and agent presence checking.
        """
        if self.running:
            return
            
        self.running = True
        
        # Start periodic discovery broadcasts
        self.discovery_task = asyncio.create_task(self._periodic_discovery_broadcast())
        
        # Start periodic presence checks
        self.presence_check_task = asyncio.create_task(self._periodic_presence_check())
        
        logger.info("Dynamic capability registry started")
        
    async def stop(self) -> None:
        """Stop the dynamic capability registry.
        
        This method stops the periodic tasks for capability broadcasting
        and agent presence checking.
        """
        if not self.running:
            return
            
        self.running = False
        
        # Cancel periodic tasks
        if self.discovery_task:
            self.discovery_task.cancel()
            try:
                await self.discovery_task
            except asyncio.CancelledError:
                pass
            self.discovery_task = None
            
        if self.presence_check_task:
            self.presence_check_task.cancel()
            try:
                await self.presence_check_task
            except asyncio.CancelledError:
                pass
            self.presence_check_task = None
            
        logger.info("Dynamic capability registry stopped")
    
    async def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[AgentCapability] | None = None,
        status: str = "active",
        resources: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentInfo:
        """Register an agent with the registry.
        
        This method extends the base implementation to update the presence monitor
        and notify subscribers of new capabilities.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type/role of the agent
            capabilities: List of agent capabilities
            status: Current operational status
            resources: Available resources and constraints
            metadata: Additional agent-specific information
            
        Returns:
            The registered agent info
        """
        agent_info = await super().register_agent(
            agent_id, agent_type, capabilities, status, resources, metadata,
        )
        
        # Update the presence monitor
        self.presence_monitor.update_agent_timestamp(agent_id)
        
        # Notify subscribers of new capabilities
        if capabilities:
            for capability in capabilities:
                await self._notify_subscribers(capability, agent_id)
                
        return agent_info
    
    async def update_agent(
        self,
        agent_id: str,
        status: str | None = None,
        resources: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentInfo | None:
        """Update an agent's information.
        
        This method extends the base implementation to update the presence monitor.
        
        Args:
            agent_id: ID of the agent to update
            status: New status (if provided)
            resources: New resources (if provided)
            metadata: New metadata (if provided)
            
        Returns:
            The updated agent info, or None if the agent is not registered
        """
        agent_info = await super().update_agent(agent_id, status, resources, metadata)
        
        if agent_info:
            # Update the presence monitor
            self.presence_monitor.update_agent_timestamp(agent_id)
            
        return agent_info
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry.
        
        This method extends the base implementation to remove the agent from
        the presence monitor.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if the agent was unregistered, False if not found
        """
        result = await super().unregister_agent(agent_id)
        
        if result:
            # Remove the agent from the presence monitor
            self.presence_monitor.remove_agent(agent_id)
            
        return result
    
    async def add_agent_capability(
        self, agent_id: str, capability: AgentCapability,
    ) -> AgentInfo | None:
        """Add a capability to an agent.
        
        This method extends the base implementation to notify subscribers
        of the new capability.
        
        Args:
            agent_id: ID of the agent to add the capability to
            capability: Capability to add
            
        Returns:
            The updated agent info, or None if the agent is not registered
        """
        agent_info = await super().add_agent_capability(agent_id, capability)
        
        if agent_info:
            # Update the presence monitor
            self.presence_monitor.update_agent_timestamp(agent_id)
            
            # Notify subscribers of the new capability
            await self._notify_subscribers(capability, agent_id)
            
        return agent_info
    
    async def subscribe_to_capabilities(
        self,
        subscriber_id: str,
        capability_types: list[str] | None = None,
        agent_ids: list[str] | None = None,
        callback: Callable[[AgentCapability, str], None] | None = None,
        expiration_minutes: int = 60,
    ) -> int:
        """Subscribe to capability updates.
        
        This method allows an agent to subscribe to capability updates for
        specific capability types or from specific agents.
        
        Args:
            subscriber_id: ID of the subscribing agent
            capability_types: Types of capabilities to subscribe to
            agent_ids: IDs of agents to subscribe to
            callback: Function to call when a matching capability is updated
            expiration_minutes: Minutes until the subscription expires
            
        Returns:
            Index of the subscription in the subscriptions list
        """
        subscription = CapabilitySubscription(
            subscriber_id=subscriber_id,
            capability_types=capability_types,
            agent_ids=agent_ids,
            callback=callback,
            expiration_minutes=expiration_minutes,
        )
        
        self.subscriptions.append(subscription)
        logger.info(
            f"Agent {subscriber_id} subscribed to capabilities: "
            f"types={capability_types}, agents={agent_ids}",
        )
        
        return len(self.subscriptions) - 1
    
    def unsubscribe(self, subscription_index: int) -> bool:
        """Unsubscribe from capability updates.
        
        Args:
            subscription_index: Index of the subscription to remove
            
        Returns:
            True if the subscription was removed, False if not found
        """
        if 0 <= subscription_index < len(self.subscriptions):
            subscription = self.subscriptions.pop(subscription_index)
            logger.info(f"Agent {subscription.subscriber_id} unsubscribed from capabilities")
            return True
        return False
    
    async def discover_capabilities(
        self,
        requester_id: str,
        capability_types: list[str] | None = None,
        agent_ids: list[str] | None = None,
        detail_level: str = "detailed",
    ) -> list[dict[str, Any]]:
        """Discover capabilities matching specific criteria.
        
        This method allows an agent to discover capabilities matching
        specific criteria without subscribing to updates.
        
        Args:
            requester_id: ID of the requesting agent
            capability_types: Types of capabilities to discover
            agent_ids: IDs of agents to discover capabilities from
            detail_level: Level of detail to include (basic, detailed, full)
            
        Returns:
            List of matching capabilities
        """
        async with self._lock:
            matching_capabilities = []
            
            for agent_id, agent_info in self.agents.items():
                # Skip if specific agent IDs were provided and this agent is not in the list
                if agent_ids and agent_id not in agent_ids:
                    continue
                    
                for capability in agent_info.capabilities:
                    # Skip if specific capability types were provided and this capability is not in the list
                    if capability_types and capability.capability_type not in capability_types:
                        continue
                        
                    # Add the capability to the results
                    cap_dict = capability.to_dict()
                    
                    # Adjust detail level
                    if detail_level == "basic":
                        cap_dict.pop("performance_metrics", None)
                        cap_dict.pop("limitations", None)
                        cap_dict.pop("parameters", None)
                    elif detail_level == "detailed":
                        # Keep most information but summarize metrics
                        pass
                    # For "full" detail level, keep everything
                    
                    # Add agent information
                    cap_dict["agent_id"] = agent_id
                    cap_dict["agent_type"] = agent_info.agent_type
                    
                    matching_capabilities.append(cap_dict)
            
            # Update the presence monitor for the requester
            self.presence_monitor.update_agent_timestamp(requester_id)
            
            return matching_capabilities
    
    async def broadcast_capability_update(
        self,
        agent_id: str,
        capabilities: list[AgentCapability],
        broadcast_type: str = "update",
    ) -> str | None:
        """Broadcast a capability update to all agents.
        
        This method allows an agent to broadcast an update to its capabilities
        to all other agents in the system.
        
        Args:
            agent_id: ID of the agent broadcasting the update
            capabilities: Updated capabilities
            broadcast_type: Type of broadcast (update, new, remove)
            
        Returns:
            The message ID of the broadcast, or None if no broadcast was sent
        """
        if not self.protocol:
            logger.error("Cannot broadcast capability update: no protocol available")
            return None
            
        # Get the agent info
        agent_info = await self.get_agent_info(agent_id)
        if not agent_info:
            logger.warning(f"Cannot broadcast capability update: agent {agent_id} not registered")
            return None
            
        # Update the capabilities in the registry
        for capability in capabilities:
            agent_info.add_capability(capability)
            
        # Update the presence monitor
        self.presence_monitor.update_agent_timestamp(agent_id)
            
        # Notify subscribers of the updated capabilities
        for capability in capabilities:
            await self._notify_subscribers(capability, agent_id)
            
        # Broadcast the update to all agents
        capability_names = [cap.name for cap in capabilities]
        return await self.broadcast_agent_discovery(
            agent_id=agent_id,
            agent_type=agent_info.agent_type,
            capabilities=capability_names,
            status=agent_info.status,
            resources=agent_info.resources,
            metadata={
                **agent_info.metadata,
                "update_type": broadcast_type,
            },
        )
    
    async def handle_agent_discovery_message(self, message: AgentDiscoveryMessage) -> None:
        """Handle an agent discovery message.
        
        This method extends the base implementation to update the presence monitor
        and handle dynamic discovery.
        
        Args:
            message: The agent discovery message to process
        """
        await super().handle_agent_discovery_message(message)
        
        # Extract agent ID from the message
        content = message.content
        agent_id = content.get("agent_id")
        
        # Update the presence monitor
        if agent_id:
            self.presence_monitor.update_agent_timestamp(agent_id)
    
    async def _notify_subscribers(self, capability: AgentCapability, agent_id: str) -> None:
        """Notify subscribers of a capability update.
        
        Args:
            capability: The updated capability
            agent_id: ID of the agent with the capability
        """
        # Remove expired subscriptions
        self.subscriptions = [s for s in self.subscriptions if not s.is_expired()]
        
        # Notify matching subscribers
        for subscription in self.subscriptions:
            if subscription.matches(capability, agent_id):
                # Update the last notified timestamp
                subscription.last_notified = datetime.utcnow()
                
                # Call the callback if provided
                if subscription.callback:
                    try:
                        subscription.callback(capability, agent_id)
                    except Exception as e:
                        logger.error(f"Error in capability subscription callback: {str(e)}")
                
                # If the protocol is available, send a capability response message
                if self.protocol:
                    try:
                        await self.protocol.send_capability_response(
                            request_id=None,  # No specific request ID for notifications
                            recipient=subscription.subscriber_id,
                            capabilities=[capability.to_dict()],
                            notification=True,  # Mark as a notification
                        )
                    except Exception as e:
                        logger.error(f"Error sending capability notification: {str(e)}")
    
    def _handle_agent_status_change(self, agent_id: str, status: str) -> None:
        """Handle a change in agent status.
        
        Args:
            agent_id: ID of the agent whose status changed
            status: New status of the agent
        """
        logger.info(f"Agent {agent_id} status changed to {status}")
        
        # Update the agent's status in the registry
        asyncio.create_task(self._update_agent_status(agent_id, status))
    
    async def _update_agent_status(self, agent_id: str, status: str) -> None:
        """Update an agent's status in the registry.
        
        Args:
            agent_id: ID of the agent to update
            status: New status of the agent
        """
        await self.update_agent(agent_id, status=status)
        
        # If the protocol is available, broadcast the status change
        if self.protocol:
            agent_info = await self.get_agent_info(agent_id)
            if agent_info:
                capability_names = [cap.name for cap in agent_info.capabilities]
                await self.broadcast_agent_discovery(
                    agent_id=agent_id,
                    agent_type=agent_info.agent_type,
                    capabilities=capability_names,
                    status=status,
                    resources=agent_info.resources,
                    metadata=agent_info.metadata,
                )
    
    async def _periodic_discovery_broadcast(self) -> None:
        """Periodically broadcast agent discovery messages.
        
        This method runs as a background task, periodically broadcasting
        discovery messages for all registered agents.
        """
        while self.running:
            try:
                # Get all active agents
                agents = await self.get_agents_by_status("active")
                
                # Broadcast discovery messages for each agent
                for agent_info in agents:
                    capability_names = [cap.name for cap in agent_info.capabilities]
                    await self.broadcast_agent_discovery(
                        agent_id=agent_info.agent_id,
                        agent_type=agent_info.agent_type,
                        capabilities=capability_names,
                        status=agent_info.status,
                        resources=agent_info.resources,
                        metadata=agent_info.metadata,
                    )
                    
                # Wait for the next broadcast interval
                await asyncio.sleep(self.broadcast_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic discovery broadcast: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def _periodic_presence_check(self) -> None:
        """Periodically check for agent presence.
        
        This method runs as a background task, periodically checking for
        agents that have timed out and updating their status.
        """
        while self.running:
            try:
                # Check for timed out agents
                timed_out_agents = self.presence_monitor.check_agent_timeouts()
                
                # Update the status of timed out agents
                for agent_id in timed_out_agents:
                    await self._update_agent_status(agent_id, "inactive")
                    
                # Wait for the next check interval (1/10 of the timeout)
                await asyncio.sleep(self.presence_monitor.timeout_seconds / 10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic presence check: {str(e)}")
                await asyncio.sleep(60)  # Wait a minute before retrying