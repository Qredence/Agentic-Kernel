"""Plugin registry for managing and discovering plugins.

This module provides a registry for managing plugins and their capabilities,
with support for A2A (Agent-to-Agent) capability advertisement and discovery.

Key features:
1. Plugin registration and discovery
2. A2A capability advertisement
3. Plugin dependency management
4. Plugin lifecycle management (initialization, cleanup)
"""

import asyncio
import logging

from ..communication.capability_registry import AgentCapability, CapabilityRegistry
from .base import BasePlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for managing plugins and their capabilities.

    This class provides a central registry for plugins, handling their
    registration, initialization, and capability advertisement through
    the A2A capability registry.

    Attributes:
        plugins: Dictionary mapping plugin names to plugin instances
        capability_registry: Reference to the A2A capability registry
    """

    def __init__(self, capability_registry: CapabilityRegistry | None = None):
        """Initialize the plugin registry.

        Args:
            capability_registry: Optional reference to the A2A capability registry
        """
        self.plugins: dict[str, BasePlugin] = {}
        self.capability_registry = capability_registry
        self._lock = asyncio.Lock()

    async def register(self, plugin_class: type[BasePlugin], **kwargs) -> BasePlugin:
        """Register a plugin with the registry.

        Args:
            plugin_class: The plugin class to register
            **kwargs: Additional arguments to pass to the plugin constructor

        Returns:
            The registered plugin instance

        Raises:
            ValueError: If a plugin with the same name is already registered
        """
        async with self._lock:
            # Create plugin instance
            plugin = plugin_class(**kwargs)
            
            # Check if plugin with same name already exists
            if plugin.name in self.plugins:
                raise ValueError(f"Plugin '{plugin.name}' is already registered")
            
            # Register plugin
            self.plugins[plugin.name] = plugin
            logger.info(f"Registered plugin: {plugin.name}")
            
            # Advertise plugin capabilities to A2A registry if available
            if self.capability_registry:
                await self._advertise_plugin_capabilities(plugin)
            
            return plugin

    async def unregister(self, plugin_name: str) -> bool:
        """Unregister a plugin from the registry.

        Args:
            plugin_name: Name of the plugin to unregister

        Returns:
            True if the plugin was unregistered, False if not found
        """
        async with self._lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Attempted to unregister unknown plugin: {plugin_name}")
                return False
            
            # Get plugin instance
            plugin = self.plugins[plugin_name]
            
            # Clean up plugin resources
            try:
                plugin.cleanup()
                logger.info(f"Cleaned up plugin: {plugin_name}")
            except Exception as e:
                logger.error(f"Error cleaning up plugin {plugin_name}: {e}")
            
            # Remove plugin from registry
            del self.plugins[plugin_name]
            logger.info(f"Unregistered plugin: {plugin_name}")
            
            return True

    async def get_plugin(self, plugin_name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            The plugin instance if found, None otherwise
        """
        async with self._lock:
            return self.plugins.get(plugin_name)

    async def get_all_plugins(self) -> list[BasePlugin]:
        """Get all registered plugins.

        Returns:
            List of all registered plugin instances
        """
        async with self._lock:
            return list(self.plugins.values())

    async def initialize_all(self) -> None:
        """Initialize all registered plugins.

        This method calls the initialize method on all registered plugins.
        """
        async with self._lock:
            for name, plugin in self.plugins.items():
                try:
                    plugin.initialize()
                    logger.info(f"Initialized plugin: {name}")
                except Exception as e:
                    logger.error(f"Error initializing plugin {name}: {e}")

    async def cleanup_all(self) -> None:
        """Clean up all registered plugins.

        This method calls the cleanup method on all registered plugins.
        """
        async with self._lock:
            for name, plugin in self.plugins.items():
                try:
                    plugin.cleanup()
                    logger.info(f"Cleaned up plugin: {name}")
                except Exception as e:
                    logger.error(f"Error cleaning up plugin {name}: {e}")

    async def _advertise_plugin_capabilities(self, plugin: BasePlugin) -> None:
        """Advertise plugin capabilities to the A2A capability registry.

        Args:
            plugin: The plugin whose capabilities to advertise
        """
        if not self.capability_registry:
            return
        
        # Get plugin capabilities
        capabilities = plugin.get_capabilities()
        
        # Convert to A2A capabilities and register with capability registry
        for cap_name, cap_desc in capabilities.items():
            capability = AgentCapability(
                name=cap_name,
                description=cap_desc,
                capability_type=self._map_to_a2a_capability_type(cap_name),
                parameters={"plugin": plugin.name},
                limitations={"provided_by_plugin": plugin.name},
                version=getattr(plugin, "version", "1.0.0"),
            )
            
            # Use a placeholder agent ID based on the plugin name
            agent_id = f"plugin.{plugin.name}"
            
            # Register capability with the A2A registry
            await self.capability_registry.add_agent_capability(agent_id, capability)
            logger.info(f"Advertised capability '{cap_name}' for plugin '{plugin.name}'")

    def _map_to_a2a_capability_type(self, capability_name: str) -> str:
        """Map a plugin capability name to an A2A capability type.

        Args:
            capability_name: The name of the plugin capability

        Returns:
            The corresponding A2A capability type
        """
        # Simple mapping based on keywords in the capability name
        if "search" in capability_name.lower():
            return "perception"
        if "summarize" in capability_name.lower() or "analyze" in capability_name.lower():
            return "reasoning"
        if "generate" in capability_name.lower():
            return "creativity"
        if "plan" in capability_name.lower():
            return "planning"
        if "memory" in capability_name.lower():
            return "memory"
        if "communicate" in capability_name.lower():
            return "communication"
        if "coordinate" in capability_name.lower():
            return "coordination"
        if "decide" in capability_name.lower():
            return "decision_making"
        if "solve" in capability_name.lower():
            return "problem_solving"
        if "learn" in capability_name.lower():
            return "learning"
        if "social" in capability_name.lower():
            return "social_intelligence"
        if "emotion" in capability_name.lower():
            return "emotional_intelligence"
        # Default to "action" for unknown capabilities
        return "action"