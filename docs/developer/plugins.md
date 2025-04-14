# Plugin System Developer Guide

## Overview

The Agentic Kernel plugin system provides a flexible way to extend the framework's functionality. This guide covers how
to develop, test, and integrate plugins into the system. The plugin system is A2A (Agent-to-Agent) compatible, allowing
plugins to advertise their capabilities through the A2A capability registry.

## Core Concepts

### Plugin Interface

Plugins must implement the base plugin interface defined in `src/agentic_kernel/plugins/base.py`:

```python
class BasePlugin:
    """Base class for all plugins in Agentic Kernel.

    This class provides the foundation for creating plugins that can be used
    by agents in the system. Plugins can advertise their capabilities through
    the A2A capability system, allowing agents to discover and use them.
    """

    def __init__(
        self, 
        name: str, 
        description: str, 
        config: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0"
    ):
        """Initialize the base plugin.

        Args:
            name: The name of the plugin.
            description: A description of what the plugin does.
            config: Optional configuration dictionary.
            version: Version of the plugin.
        """
        self.name = name
        self.description = description
        self.config = config or {}
        self.version = version

        # A2A capability types that this plugin can provide
        self.a2a_capability_types: Set[str] = set()

    def validate_config(self) -> bool:
        """Validate the plugin configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return True

    def get_capabilities(self) -> Dict[str, str]:
        """Get a dictionary of plugin capabilities.

        This method should be overridden by subclasses to provide information
        about the capabilities offered by the plugin. These capabilities will
        be advertised through the A2A capability registry.

        Returns:
            Dict[str, str]: A dictionary mapping capability names to descriptions.
        """
        return {}

    def get_a2a_capability_types(self) -> Set[str]:
        """Get the A2A capability types supported by this plugin.

        Returns:
            Set[str]: Set of A2A capability type names
        """
        return self.a2a_capability_types

    def set_a2a_capability_types(self, capability_types: Set[str]) -> None:
        """Set the A2A capability types supported by this plugin.

        Args:
            capability_types: Set of A2A capability type names
        """
        self.a2a_capability_types = capability_types

    def get_dependencies(self) -> List[str]:
        """Get the dependencies of this plugin.

        Returns:
            List[str]: List of plugin names that this plugin depends on
        """
        return []

    def initialize(self) -> None:
        """Initialize the plugin. Called after configuration is set."""
        pass

    def cleanup(self) -> None:
        """Clean up any resources used by the plugin."""
        pass
```

### Plugin Registry

The plugin registry manages plugin lifecycle and A2A capability advertisement:

- Plugin registration and discovery
- A2A capability advertisement through the capability registry
- Dependency resolution
- Initialization order
- Resource cleanup

The `PluginRegistry` class is defined in `src/agentic_kernel/plugins/registry.py`:

```python
class PluginRegistry:
    """Registry for managing plugins and their capabilities.

    This class provides a central registry for plugins, handling their
    registration, initialization, and capability advertisement through
    the A2A capability registry.
    """

    def __init__(self, capability_registry: Optional[CapabilityRegistry] = None):
        """Initialize the plugin registry.

        Args:
            capability_registry: Optional reference to the A2A capability registry
        """
        self.plugins: Dict[str, BasePlugin] = {}
        self.capability_registry = capability_registry
        self._lock = asyncio.Lock()

    async def register(self, plugin_class: Type[BasePlugin], **kwargs) -> BasePlugin:
        """Register a plugin with the registry.

        Args:
            plugin_class: The plugin class to register
            **kwargs: Additional arguments to pass to the plugin constructor

        Returns:
            The registered plugin instance
        """
        # Implementation details...

    async def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin to get

        Returns:
            The plugin instance if found, None otherwise
        """
        # Implementation details...
```

When a plugin is registered with the `PluginRegistry`, its capabilities are automatically advertised through the A2A
capability registry if one is provided. This allows agents to discover and use the plugin's capabilities through the A2A
capability system.

### Configuration Management

Plugins can define their configuration schema and access configuration values through the configuration system.

## Development Guide

### Creating a New Plugin

1. Create a new module in `src/agentic_kernel/plugins/`
2. Implement the `BasePlugin` interface
3. Define configuration schema
4. Implement plugin functionality
5. Add tests in `tests/plugins/`

### Example Plugin

```python
from agentic_kernel.plugins.base import BasePlugin
from agentic_kernel.config_types import PluginConfig

class ExamplePlugin(BasePlugin):
    """Example plugin implementation."""

    def __init__(self, config: PluginConfig):
        self._config = config
        self._initialized = False

    @property
    def name(self) -> str:
        return "example_plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def initialize(self) -> None:
        if self._initialized:
            return

        # Plugin initialization logic
        self._initialized = True

    async def cleanup(self) -> None:
        if not self._initialized:
            return

        # Plugin cleanup logic
        self._initialized = False
```

### Plugin Configuration

Define plugin configuration in `pyproject.toml`:

```toml
[tool.agentic_kernel.plugins.example_plugin]
enabled = true
option1 = "value1"
option2 = "value2"
```

### Plugin Testing

Create comprehensive tests for your plugin:

```python
import pytest
from agentic_kernel.plugins import ExamplePlugin
from agentic_kernel.config_types import PluginConfig

@pytest.fixture
def plugin_config():
    return PluginConfig(
        enabled=True,
        options={
            "option1": "value1",
            "option2": "value2"
        }
    )

@pytest.fixture
def plugin(plugin_config):
    return ExamplePlugin(plugin_config)

@pytest.mark.asyncio
async def test_plugin_initialization(plugin):
    assert not plugin._initialized
    await plugin.initialize()
    assert plugin._initialized

@pytest.mark.asyncio
async def test_plugin_cleanup(plugin):
    await plugin.initialize()
    assert plugin._initialized
    await plugin.cleanup()
    assert not plugin._initialized
```

## Integration Guide

### Registering Plugins

Register plugins with the plugin registry:

```python
from agentic_kernel.plugins import PluginRegistry
from example_plugin import ExamplePlugin

registry = PluginRegistry()
registry.register(ExamplePlugin)
```

### Plugin Dependencies

Specify plugin dependencies:

```python
class DependentPlugin(BasePlugin):
    """Plugin that depends on ExamplePlugin."""

    @property
    def dependencies(self) -> List[str]:
        return ["example_plugin"]
```

### Error Handling

Handle plugin errors gracefully:

```python
try:
    await plugin.initialize()
except PluginInitializationError as e:
    logger.error(f"Failed to initialize plugin: {e}")
    # Handle initialization failure
```

## Best Practices

1. **Documentation**
   - Document plugin purpose and functionality
   - Include configuration examples
   - Provide usage examples

2. **Error Handling**
   - Use specific exception types
   - Provide detailed error messages
   - Clean up resources on failure

3. **Testing**
   - Write comprehensive unit tests
   - Test configuration handling
   - Test error conditions

4. **Performance**
   - Minimize initialization overhead
   - Clean up resources properly
   - Use async operations appropriately

5. **Security**
   - Validate configuration values
   - Handle sensitive data securely
   - Implement proper access controls

## Common Patterns

### State Management

```python
class StatefulPlugin(BasePlugin):
    def __init__(self, config: PluginConfig):
        self._state = {}
        self._lock = asyncio.Lock()

    async def set_state(self, key: str, value: Any) -> None:
        async with self._lock:
            self._state[key] = value

    async def get_state(self, key: str) -> Any:
        async with self._lock:
            return self._state.get(key)
```

### Resource Management

```python
class ResourcePlugin(BasePlugin):
    async def initialize(self) -> None:
        self._resource = await self._create_resource()
        try:
            await self._setup_resource()
        except Exception:
            await self._cleanup_resource()
            raise

    async def cleanup(self) -> None:
        await self._cleanup_resource()
```

### Event Handling

```python
class EventPlugin(BasePlugin):
    def __init__(self, config: PluginConfig):
        self._handlers = {}

    def register_handler(self, event: str, handler: Callable) -> None:
        self._handlers[event] = handler

    async def handle_event(self, event: str, data: Any) -> None:
        if handler := self._handlers.get(event):
            await handler(data)
```

## Troubleshooting

Common issues and solutions:

1. **Plugin Not Loading**
   - Check configuration
   - Verify dependencies
   - Check initialization order

2. **Resource Leaks**
   - Implement proper cleanup
   - Use context managers
   - Monitor resource usage

3. **Performance Issues**
   - Profile initialization
   - Optimize resource usage
   - Use caching when appropriate
``` 
