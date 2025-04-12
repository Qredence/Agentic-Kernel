# Agent Module

This module provides the core agent functionality for the Agentic-Kernel system, including the base agent class, specialized agent implementations, and role management.

## Key Components

### Base Agent

The `base.py` file defines the `BaseAgent` class that all specialized agents must inherit from. It provides:

- Task execution interface
- Task validation
- Pre/post processing hooks
- Capability reporting
- Configuration management
- Inter-agent communication

### Role Management

The `role_manager.py` file implements agent specialization and role assignment based on capabilities:

- Role definition with capability requirements
- Role assignment based on agent capabilities
- Role-based task delegation
- Role compatibility checking

## Usage Examples

### Creating a Specialized Agent

```python
from agentic_kernel.agents.base import BaseAgent
from agentic_kernel.types import Task

class DataProcessorAgent(BaseAgent):
    async def execute(self, task: Task) -> Dict[str, Any]:
        # Process the data according to task parameters
        result = await self._process_data(task.parameters["data"])
        return {
            "status": "completed",
            "output": result,
            "metrics": {"processing_time": 1.5}
        }
    
    def _get_supported_tasks(self) -> Dict[str, TaskCapability]:
        return {
            "process_data": {
                "description": "Process input data",
                "parameters": ["data"],
                "optional_parameters": ["format"],
                "examples": [
                    {"data": "sample_data", "format": "json"}
                ]
            }
        }
```

### Defining and Assigning Roles

```python
from agentic_kernel.agents.role_manager import AgentRole, RoleManager
from agentic_kernel.communication.capability_registry import CapabilityRegistry

# Create a capability registry
registry = CapabilityRegistry()

# Create a role manager
role_manager = RoleManager(registry)

# Define roles with required capabilities
data_processor_role = AgentRole(
    name="Data Processor",
    description="Processes and transforms data",
    required_capabilities={"data_processing", "file_handling"},
    preferred_capabilities={"data_visualization"}
)

data_analyzer_role = AgentRole(
    name="Data Analyzer",
    description="Analyzes data and generates insights",
    required_capabilities={"data_analysis", "statistical_modeling"},
    preferred_capabilities={"machine_learning", "data_visualization"}
)

# Add roles to the manager
role_manager.add_role(data_processor_role)
role_manager.add_role(data_analyzer_role)

# Assign roles to agents based on their capabilities
await role_manager.assign_role_to_agent("agent1", "data_processor")
await role_manager.assign_role_to_agent("agent2", "data_analyzer")

# Automatically assign roles to all agents based on capabilities
await role_manager.auto_assign_roles()

# Find the best agent for a specific role
best_agent, score = await role_manager.find_best_agent_for_role("data_processor")
print(f"Best agent for data processing: {best_agent.agent_id} (score: {score})")
```

### Finding Agents by Role

```python
# Find all agents compatible with a role
compatible_agents = await role_manager.find_agents_for_role("data_processor")
for agent, score in compatible_agents:
    print(f"Agent {agent.agent_id} is compatible with score {score}")

# Get all roles assigned to an agent
agent_roles = await role_manager.get_agent_roles("agent1")
for role in agent_roles:
    print(f"Agent has role: {role.name}")
```

## Role-Based Task Delegation

The role management system enables intelligent task delegation based on agent capabilities and assigned roles:

1. Define roles with specific capability requirements
2. Register agents with their capabilities in the capability registry
3. Assign roles to agents based on their capabilities
4. When a task needs to be performed, find the best agent for the role required by the task
5. Delegate the task to the selected agent

This approach ensures that tasks are assigned to the most capable agents, improving overall system performance and reliability.