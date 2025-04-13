# Agent Configuration Options

## Introduction

This document provides a comprehensive guide to the configuration options available for agents in the Agentic Kernel
system and explains how these options affect agent behavior and collaboration. Understanding these configuration options
is essential for optimizing agent performance and enabling effective multi-agent collaboration.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Common Configuration Options](#common-configuration-options)
3. [Agent-Specific Configuration Options](#agent-specific-configuration-options)
4. [A2A Protocol Configuration](#a2a-protocol-configuration)
5. [Communication Configuration](#communication-configuration)
6. [Performance Configuration](#performance-configuration)
7. [Security Configuration](#security-configuration)
8. [Collaboration Effects](#collaboration-effects)
9. [Configuration Best Practices](#configuration-best-practices)
10. [Examples](#examples)

## Configuration Overview

Agent configuration in the Agentic Kernel system is managed through a combination of:

1. **System-wide configuration**: Global settings that apply to all agents
2. **Agent-specific configuration**: Settings that apply to specific agent types
3. **Instance configuration**: Settings that apply to individual agent instances
4. **Runtime configuration**: Settings that can be modified during agent execution

Configuration is typically defined in YAML or JSON format and loaded at agent initialization time. The configuration
system supports environment variable substitution, allowing for flexible deployment across different environments.

## Common Configuration Options

These configuration options are common to all agent types:

### Basic Agent Configuration

```yaml
agent:
  name: "MyAgent"                  # Agent name (required)
  description: "My custom agent"   # Agent description (optional)
  version: "1.0.0"                 # Agent version (required)
  type: "custom"                   # Agent type (required)
  enabled: true                    # Whether the agent is enabled (default: true)
  timeout: 60                      # Default timeout in seconds (default: 30)
  max_retries: 3                   # Maximum number of retries (default: 3)
  retry_delay: 5                   # Delay between retries in seconds (default: 1)
```

### Logging Configuration

```yaml
logging:
  level: "INFO"                    # Logging level (default: INFO)
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/path/to/log/file.log"    # Log file path (optional)
  console: true                    # Log to console (default: true)
  include_timestamps: true         # Include timestamps in logs (default: true)
```

### Memory Configuration

```yaml
memory:
  type: "in_memory"                # Memory type (default: in_memory)
  persistence: true                # Whether to persist memory (default: false)
  storage_path: "/path/to/storage" # Path for persistent storage (required if persistence is true)
  max_size: 1000                   # Maximum number of items to store (default: 1000)
  ttl: 3600                        # Time-to-live in seconds (default: 3600)
```

## Agent-Specific Configuration Options

Different agent types have specific configuration options:

### CoderAgent Configuration

```yaml
coder:
  language_model: "gpt-4"          # Language model to use (default: gpt-4)
  temperature: 0.2                 # Temperature for code generation (default: 0.2)
  max_tokens: 8192                 # Maximum tokens for code generation (default: 4096)
  supported_languages:             # Supported programming languages
    - python
    - javascript
    - typescript
    - java
  code_style: "pep8"               # Code style for formatting (default: depends on language)
  include_comments: true           # Whether to include comments in code (default: true)
  test_generation: true            # Whether to generate tests (default: false)
```

### WebSurferAgent Configuration

```yaml
web_surfer:
  user_agent: "Mozilla/5.0 ..."    # User agent string (default: standard user agent)
  timeout: 30                      # Request timeout in seconds (default: 30)
  max_retries: 3                   # Maximum number of retries (default: 3)
  follow_redirects: true           # Whether to follow redirects (default: true)
  max_redirects: 5                 # Maximum number of redirects to follow (default: 5)
  headers:                         # Default headers to include in requests
    Accept: "text/html,application/xhtml+xml,application/xml"
    Accept-Language: "en-US,en;q=0.9"
  cookies_enabled: true            # Whether to enable cookies (default: true)
  javascript_enabled: true         # Whether to enable JavaScript (default: true)
```

### FileSurferAgent Configuration

```yaml
file_surfer:
  base_directory: "/path/to/files" # Base directory for file operations (required)
  allowed_extensions:              # Allowed file extensions (default: all)
    - .txt
    - .md
    - .py
    - .js
  max_file_size: 10485760          # Maximum file size in bytes (default: 10MB)
  encoding: "utf-8"                # Default file encoding (default: utf-8)
  create_directories: true         # Whether to create directories (default: false)
  backup_files: true               # Whether to backup files before modification (default: true)
  backup_directory: ".backups"     # Directory for backups (default: .backups)
```

### TerminalAgent Configuration

```yaml
terminal:
  shell: "/bin/bash"               # Shell to use (default: system default)
  working_directory: "/path/to/dir" # Working directory (default: current directory)
  environment:                     # Environment variables
    PATH: "/usr/local/bin:/usr/bin:/bin"
    PYTHONPATH: "/path/to/python/modules"
  timeout: 60                      # Command timeout in seconds (default: 30)
  max_output_size: 10485760        # Maximum output size in bytes (default: 10MB)
  allowed_commands:                # Allowed commands (default: all)
    - ls
    - grep
    - find
  blocked_commands:                # Blocked commands (default: none)
    - rm -rf /
    - shutdown
  sudo_allowed: false              # Whether sudo is allowed (default: false)
```

## A2A Protocol Configuration

These options configure the A2A protocol implementation:

```yaml
a2a:
  enabled: true                    # Whether A2A protocol is enabled (default: true)
  host: "0.0.0.0"                  # Host to bind the A2A server to (default: 0.0.0.0)
  port: 8000                       # Port to bind the A2A server to (default: 8000)
  base_url: "http://localhost:8000" # Base URL for the A2A server (required)
  authentication:                  # Authentication configuration
    type: "api_key"                # Authentication type (default: none)
    api_key_header: "X-API-Key"    # API key header name (default: X-API-Key)
    api_key: "${API_KEY}"          # API key value (environment variable)
  capabilities:                    # Agent capabilities
    streaming: true                # Whether streaming is supported (default: false)
    push_notifications: false      # Whether push notifications are supported (default: false)
    state_transition_history: true # Whether state transition history is supported (default: false)
  default_input_modes:             # Default input modes
    - text
  default_output_modes:            # Default output modes
    - text
  task_manager:                    # Task manager configuration
    type: "in_memory"              # Task manager type (default: in_memory)
    persistence: false             # Whether to persist tasks (default: false)
    storage_path: "/path/to/storage" # Path for persistent storage (required if persistence is true)
    max_tasks: 1000                # Maximum number of tasks to store (default: 1000)
    task_ttl: 3600                 # Task time-to-live in seconds (default: 3600)
```

## Communication Configuration

These options configure how agents communicate with each other:

```yaml
communication:
  protocol: "a2a"                  # Communication protocol (default: a2a)
  message_format: "json"           # Message format (default: json)
  compression: false               # Whether to compress messages (default: false)
  encryption: false                # Whether to encrypt messages (default: false)
  timeout: 30                      # Communication timeout in seconds (default: 30)
  retry:                           # Retry configuration
    max_retries: 3                 # Maximum number of retries (default: 3)
    retry_delay: 1                 # Delay between retries in seconds (default: 1)
    backoff_factor: 2              # Backoff factor for retries (default: 2)
  rate_limiting:                   # Rate limiting configuration
    enabled: true                  # Whether rate limiting is enabled (default: false)
    max_requests: 100              # Maximum number of requests per period (default: 100)
    period: 60                     # Period in seconds (default: 60)
```

## Performance Configuration

These options configure agent performance characteristics:

```yaml
performance:
  concurrency: 10                  # Maximum number of concurrent tasks (default: 5)
  batch_size: 5                    # Batch size for processing (default: 1)
  prefetch: true                   # Whether to prefetch data (default: false)
  caching:                         # Caching configuration
    enabled: true                  # Whether caching is enabled (default: false)
    ttl: 3600                      # Cache time-to-live in seconds (default: 3600)
    max_size: 1000                 # Maximum cache size (default: 1000)
  resource_limits:                 # Resource limits
    cpu: 2                         # Maximum CPU cores (default: unlimited)
    memory: "2G"                   # Maximum memory (default: unlimited)
    disk: "10G"                    # Maximum disk space (default: unlimited)
```

## Security Configuration

These options configure agent security:

```yaml
security:
  authentication:                  # Authentication configuration
    enabled: true                  # Whether authentication is enabled (default: true)
    type: "api_key"                # Authentication type (default: api_key)
    api_key_header: "X-API-Key"    # API key header name (default: X-API-Key)
    api_key: "${API_KEY}"          # API key value (environment variable)
  authorization:                   # Authorization configuration
    enabled: true                  # Whether authorization is enabled (default: false)
    roles:                         # Role definitions
      admin:                       # Admin role
        permissions:               # Admin permissions
          - "read:*"
          - "write:*"
          - "execute:*"
      user:                        # User role
        permissions:               # User permissions
          - "read:*"
          - "write:own"
          - "execute:safe"
  input_validation:                # Input validation configuration
    enabled: true                  # Whether input validation is enabled (default: true)
    sanitize_input: true           # Whether to sanitize input (default: true)
    max_input_size: 1048576        # Maximum input size in bytes (default: 1MB)
  output_validation:               # Output validation configuration
    enabled: true                  # Whether output validation is enabled (default: true)
    sanitize_output: true          # Whether to sanitize output (default: true)
    max_output_size: 1048576       # Maximum output size in bytes (default: 1MB)
```

## Collaboration Effects

Different configuration options can significantly affect how agents collaborate with each other. Here are some key
effects:

### Communication Protocol Configuration

The A2A protocol configuration determines how agents discover and communicate with each other:

- **Streaming**: When enabled, allows agents to provide incremental updates for long-running tasks, improving
  responsiveness in collaborative workflows.
- **Push Notifications**: When enabled, allows agents to notify other agents of events asynchronously, reducing polling
  and improving efficiency.
- **State Transition History**: When enabled, provides a complete history of task state transitions, helping with
  debugging and auditing collaborative workflows.

### Agent Capabilities

Agent capabilities affect what types of tasks an agent can perform and how it can collaborate:

- **Input/Output Modes**: Determine what types of data an agent can accept and produce, affecting compatibility with
  other agents.
- **Skills**: Define the specific capabilities an agent provides, helping other agents discover and utilize its
  functionality.
- **Authentication Requirements**: Determine how agents authenticate with each other, affecting security and trust.

### Performance Configuration

Performance configuration affects how efficiently agents can collaborate:

- **Concurrency**: Higher concurrency allows an agent to handle more tasks simultaneously, improving throughput in
  collaborative workflows.
- **Caching**: Enables agents to cache results, reducing redundant work and improving response times.
- **Resource Limits**: Prevent individual agents from consuming too many resources, ensuring fair allocation in
  multi-agent systems.

### Timeout and Retry Configuration

Timeout and retry settings affect the reliability of agent collaboration:

- **Timeouts**: Prevent agents from waiting indefinitely for responses, improving resilience to failures.
- **Retries**: Allow agents to automatically retry failed operations, improving reliability in distributed systems.
- **Backoff Strategies**: Prevent overloading systems during retries, improving stability under load.

## Configuration Best Practices

1. **Use Environment Variables for Sensitive Information**: Store API keys, passwords, and other sensitive information
   in environment variables rather than hardcoding them in configuration files.

2. **Start with Default Values**: Begin with the default configuration values and adjust only as needed based on
   observed performance and requirements.

3. **Configure Timeouts Appropriately**: Set timeouts based on expected operation times, with some margin for network
   latency and processing time.

4. **Enable Logging for Debugging**: Use detailed logging during development and testing to diagnose issues, but reduce
   logging verbosity in production to improve performance.

5. **Limit Resource Usage**: Configure resource limits to prevent agents from consuming excessive resources, especially
   in shared environments.

6. **Implement Rate Limiting**: Use rate limiting to prevent agents from overwhelming external services or each other
   with too many requests.

7. **Configure Authentication and Authorization**: Always enable authentication and authorization in production
   environments to secure agent communication.

8. **Use Consistent Configuration Across Related Agents**: Ensure that agents that frequently collaborate have
   compatible configuration settings.

9. **Document Custom Configuration**: Document any custom configuration settings to help other developers understand
   your agent's behavior.

10. **Validate Configuration at Startup**: Validate configuration at startup to catch errors early and provide clear
    error messages.

## Examples

### Basic Agent Configuration Example

```yaml
# config.yaml
agent:
  name: "CodeAssistant"
  description: "An agent that assists with coding tasks"
  version: "1.0.0"
  type: "coder"
  timeout: 120
  max_retries: 3

logging:
  level: "INFO"
  file: "logs/coder_agent.log"

coder:
  language_model: "gpt-4"
  temperature: 0.2
  supported_languages:
    - python
    - javascript
    - typescript
  code_style: "pep8"
  include_comments: true
  test_generation: true

a2a:
  enabled: true
  port: 8001
  base_url: "http://localhost:8001"
  capabilities:
    streaming: true
    push_notifications: false
    state_transition_history: true
  default_input_modes:
    - text
  default_output_modes:
    - text
    - code
```

### Loading Configuration in Python

```python
import yaml
from agentic_kernel.config.loader import ConfigLoader

# Load configuration from file
with open("config.yaml", "r") as f:
    config_data = yaml.safe_load(f)

# Create config loader
config_loader = ConfigLoader(config_data)

# Get agent configuration
agent_config = config_loader.get_agent_config()
print(f"Agent name: {agent_config.name}")
print(f"Agent timeout: {agent_config.timeout} seconds")

# Get coder-specific configuration
coder_config = config_loader.get_agent_type_config("coder")
print(f"Language model: {coder_config.language_model}")
print(f"Supported languages: {', '.join(coder_config.supported_languages)}")

# Get A2A configuration
a2a_config = config_loader.get_a2a_config()
print(f"A2A port: {a2a_config.port}")
print(f"Streaming enabled: {a2a_config.capabilities.streaming}")
```

### Configuration for Collaborative Workflow

```yaml
# Orchestrator Agent Configuration
orchestrator:
  name: "WorkflowOrchestrator"
  description: "Orchestrates multi-agent workflows"
  version: "1.0.0"
  type: "orchestrator"
  timeout: 300  # Longer timeout for coordinating complex workflows

  a2a:
    port: 8000
    base_url: "http://localhost:8000"
    capabilities:
      streaming: true
      state_transition_history: true

  performance:
    concurrency: 20  # Handle multiple agent interactions simultaneously
    caching:
      enabled: true
      ttl: 3600

# Coder Agent Configuration
coder:
  name: "CodeGenerator"
  description: "Generates code based on requirements"
  version: "1.0.0"
  type: "coder"
  timeout: 120

  a2a:
    port: 8001
    base_url: "http://localhost:8001"
    capabilities:
      streaming: true

  coder:
    language_model: "gpt-4"
    temperature: 0.2
    supported_languages:
      - python
      - javascript

# Terminal Agent Configuration
terminal:
  name: "CommandExecutor"
  description: "Executes commands in a secure environment"
  version: "1.0.0"
  type: "terminal"
  timeout: 60

  a2a:
    port: 8002
    base_url: "http://localhost:8002"
    capabilities:
      streaming: true

  terminal:
    shell: "/bin/bash"
    working_directory: "/workspace"
    allowed_commands:
      - python
      - npm
      - git
```

By understanding and properly configuring these options, you can optimize agent behavior and enable effective
collaboration between agents in the Agentic Kernel system.