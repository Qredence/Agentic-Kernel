# Agent Communication Protocols in AgenticKernel

This guide covers the communication protocols and interaction patterns available in AgenticKernel, including A2A (
Agent-to-Agent) protocol support.

## Supported Protocols

- **A2A (Agent-to-Agent):** HTTP/JSON-RPC 2.0 based protocol for agent interoperability. Key features include discovery,
  tasks, messages, artifacts, lifecycle states, and streaming.
- **Custom Protocols:** Extendable via plugins for custom agent communication.

## Key Concepts

- **AgentCard:** Published at `/.well-known/agent.json` for discovery.
- **Task Lifecycle:** States like `submitted`, `working`, `completed`.
- **Messages & Artifacts:** Rich data exchange between agents.

For implementation details,
see [developer/agent_communication_protocols.md](../../developer/agent_communication_protocols.md)
and [developer/creating_a2a_compatible_agents.md](../../developer/creating_a2a_compatible_agents.md).
