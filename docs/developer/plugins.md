# Plugin System Developer Guide

## Overview

The Agentic Kernel plugin system provides a flexible way to extend the framework's functionality. This guide covers how to develop, test, and integrate plugins into the system.

## Core Concepts

### Plugin Interface

Plugins must implement the base plugin interface defined in `src/agentic_kernel/plugins/base.py`:

```python
class BasePlugin:
    """Base class for all plugins."""
    
    async def initialize(self) -> None:
        """Initialize the plugin."""
        pass
        
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
        
    @property
    def name(self) -> str:
        """Return the plugin name."""
        raise NotImplementedError
        
    @property
    def version(self) -> str:
        """Return the plugin version."""
        raise NotImplementedError
```

### Plugin Registry

The plugin registry manages plugin lifecycle:

- Plugin registration
- Dependency resolution
- Initialization order
- Resource cleanup

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