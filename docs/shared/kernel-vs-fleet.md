# AgenticKernel vs AgenticFleet

This page clarifies the distinction and relationship between AgenticKernel and AgenticFleet.

## AgenticKernel

- Core engine for agent-based systems
- Handles agent communication, task management, memory, plugins
- Designed for composability and extensibility
- Suitable for single agents or small agent groups

## AgenticFleet

- Built on top of AgenticKernel
- Manages large-scale agent deployments ("fleets")
- Adds features for monitoring, scaling, distributed workflows
- Integrates with cloud and enterprise systems

## Interoperability

- AgenticFleet uses AgenticKernel as its foundation
- Both support the A2A protocol for agent interoperability
- You can use AgenticKernel standalone or as part of a Fleet

---
See also: [AgenticKernel Introduction](../agentic-kernel/introduction.md)
