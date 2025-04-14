# Agent Interaction Patterns

## Introduction

This document provides architecture diagrams and explanations of agent interaction patterns in the Agentic Kernel
system. These patterns illustrate how agents communicate and collaborate to accomplish complex tasks using the A2A
protocol.

## Table of Contents

1. [Basic Interaction Patterns](#basic-interaction-patterns)
2. [Workflow Execution Patterns](#workflow-execution-patterns)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Streaming and Push Notification Patterns](#streaming-and-push-notification-patterns)
5. [Agent Discovery and Capability Negotiation](#agent-discovery-and-capability-negotiation)
6. [Multi-Agent Collaboration Patterns](#multi-agent-collaboration-patterns)

## Basic Interaction Patterns

### Request-Response Pattern

The simplest interaction pattern is the request-response pattern, where one agent sends a request to another agent and
receives a response.

```mermaid
sequenceDiagram
    participant Client
    participant Server
    
    Client->>Server: JSON-RPC Request
    Note right of Server: Process request
    Server->>Client: JSON-RPC Response
```

### Task Assignment Pattern

The task assignment pattern is used when one agent assigns a task to another agent.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Agent
    
    Orchestrator->>Agent: tasks/send (Task Assignment)
    Note right of Agent: Process task
    Agent->>Orchestrator: Task Response (Completed/Failed)
```

### Query-Response Pattern

The query-response pattern is used when one agent needs information from another agent.

```mermaid
sequenceDiagram
    participant AgentA
    participant AgentB
    
    AgentA->>AgentB: Query for Information
    Note right of AgentB: Process query
    AgentB->>AgentA: Response with Information
```

## Workflow Execution Patterns

### Sequential Task Execution

In sequential task execution, tasks are executed one after another, with each task depending on the completion of the
previous task.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    participant AgentC
    
    Orchestrator->>AgentA: Task 1 Assignment
    Note right of AgentA: Process Task 1
    AgentA->>Orchestrator: Task 1 Completed
    
    Orchestrator->>AgentB: Task 2 Assignment
    Note right of AgentB: Process Task 2
    AgentB->>Orchestrator: Task 2 Completed
    
    Orchestrator->>AgentC: Task 3 Assignment
    Note right of AgentC: Process Task 3
    AgentC->>Orchestrator: Task 3 Completed
```

### Parallel Task Execution

In parallel task execution, multiple tasks are executed simultaneously by different agents.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    participant AgentC
    
    Orchestrator->>AgentA: Task 1 Assignment
    Orchestrator->>AgentB: Task 2 Assignment
    Orchestrator->>AgentC: Task 3 Assignment
    
    Note right of AgentA: Process Task 1
    Note right of AgentB: Process Task 2
    Note right of AgentC: Process Task 3
    
    AgentA->>Orchestrator: Task 1 Completed
    AgentB->>Orchestrator: Task 2 Completed
    AgentC->>Orchestrator: Task 3 Completed
```

### Dependency-Based Task Execution

In dependency-based task execution, tasks are executed based on their dependencies, with some tasks running in parallel
and others sequentially.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    participant AgentC
    participant AgentD
    
    Orchestrator->>AgentA: Task 1 Assignment
    Orchestrator->>AgentB: Task 2 Assignment
    
    Note right of AgentA: Process Task 1
    Note right of AgentB: Process Task 2
    
    AgentA->>Orchestrator: Task 1 Completed
    AgentB->>Orchestrator: Task 2 Completed
    
    Orchestrator->>AgentC: Task 3 Assignment (depends on Task 1)
    Orchestrator->>AgentD: Task 4 Assignment (depends on Task 2)
    
    Note right of AgentC: Process Task 3
    Note right of AgentD: Process Task 4
    
    AgentC->>Orchestrator: Task 3 Completed
    AgentD->>Orchestrator: Task 4 Completed
```

## Error Handling Patterns

### Retry Pattern

The retry pattern is used when a task fails and needs to be retried.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant Agent
    
    Orchestrator->>Agent: Task Assignment
    Note right of Agent: Process task
    Agent->>Orchestrator: Task Failed
    
    Note left of Orchestrator: Retry logic
    Orchestrator->>Agent: Task Assignment (Retry)
    Note right of Agent: Process task again
    Agent->>Orchestrator: Task Completed
```

### Fallback Pattern

The fallback pattern is used when a task fails and an alternative approach is needed.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    
    Orchestrator->>AgentA: Task Assignment
    Note right of AgentA: Process task
    AgentA->>Orchestrator: Task Failed
    
    Note left of Orchestrator: Fallback logic
    Orchestrator->>AgentB: Alternative Task Assignment
    Note right of AgentB: Process alternative task
    AgentB->>Orchestrator: Task Completed
```

### Error Recovery Pattern

The error recovery pattern is used when a task fails and requires intervention from another agent to recover.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    
    Orchestrator->>AgentA: Task Assignment
    Note right of AgentA: Process task
    AgentA->>Orchestrator: Task Failed (with error details)
    
    Orchestrator->>AgentB: Error Recovery Task
    Note right of AgentB: Analyze and fix error
    AgentB->>Orchestrator: Recovery Completed
    
    Orchestrator->>AgentA: Task Assignment (with fixed parameters)
    Note right of AgentA: Process task with fixes
    AgentA->>Orchestrator: Task Completed
```

## Streaming and Push Notification Patterns

### Streaming Updates Pattern

The streaming updates pattern is used for long-running tasks where the agent provides incremental updates to the client.

```mermaid
sequenceDiagram
    participant Client
    participant Server
    
    Client->>Server: tasks/sendSubscribe
    
    Note right of Server: Start processing
    Server->>Client: Status Update (WORKING)
    
    Note right of Server: Intermediate progress
    Server->>Client: Artifact Update (partial result)
    
    Note right of Server: More progress
    Server->>Client: Artifact Update (more results)
    
    Note right of Server: Task completed
    Server->>Client: Status Update (COMPLETED)
    Server->>Client: Final Artifact
```

### Push Notification Pattern

The push notification pattern is used when an agent needs to notify a client of asynchronous events.

```mermaid
sequenceDiagram
    participant Client
    participant Server
    participant NotificationEndpoint
    
    Client->>Server: tasks/send (with push_notification config)
    Server->>Client: Task Accepted
    
    Note right of Server: Start processing
    Server->>NotificationEndpoint: Status Update (WORKING)
    
    Note right of Server: Progress
    Server->>NotificationEndpoint: Artifact Update
    
    Note right of Server: Task completed
    Server->>NotificationEndpoint: Status Update (COMPLETED)
```

## Agent Discovery and Capability Negotiation

### Agent Discovery Pattern

The agent discovery pattern is used when a client needs to discover the capabilities of an agent.

```mermaid
sequenceDiagram
    participant Client
    participant Server
    
    Client->>Server: agent/getCard
    Server->>Client: Agent Card (capabilities, skills, etc.)
    
    Note left of Client: Analyze capabilities
    Client->>Server: tasks/send (compatible with capabilities)
```

### Capability Negotiation Pattern

The capability negotiation pattern is used when agents need to negotiate how they will interact.

```mermaid
sequenceDiagram
    participant AgentA
    participant AgentB
    
    AgentA->>AgentB: agent/getCard
    AgentB->>AgentA: Agent Card (capabilities, skills, etc.)
    
    Note left of AgentA: Determine compatible interaction mode
    AgentA->>AgentB: tasks/send (with negotiated parameters)
```

## Multi-Agent Collaboration Patterns

### Team Collaboration Pattern

The team collaboration pattern involves multiple agents working together as a team, coordinated by an orchestrator.

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant AgentA
    participant AgentB
    participant AgentC
    
    User->>Orchestrator: Complex Task
    
    Orchestrator->>AgentA: Subtask 1
    Orchestrator->>AgentB: Subtask 2
    
    AgentA->>Orchestrator: Subtask 1 Result
    AgentB->>Orchestrator: Subtask 2 Result
    
    Orchestrator->>AgentC: Integration Task
    AgentC->>Orchestrator: Integrated Result
    
    Orchestrator->>User: Final Result
```

### Peer-to-Peer Collaboration Pattern

The peer-to-peer collaboration pattern involves agents communicating directly with each other without a central
orchestrator.

```mermaid
sequenceDiagram
    participant AgentA
    participant AgentB
    participant AgentC
    
    AgentA->>AgentB: Request Information
    AgentB->>AgentA: Provide Information
    
    AgentA->>AgentC: Request Processing
    AgentC->>AgentA: Processing Result
    
    AgentB->>AgentC: Coordinate Action
    AgentC->>AgentB: Action Confirmation
```

### Consensus-Based Collaboration Pattern

The consensus-based collaboration pattern involves agents reaching consensus on a decision or action.

```mermaid
sequenceDiagram
    participant Orchestrator
    participant AgentA
    participant AgentB
    participant AgentC
    
    Orchestrator->>AgentA: Request Opinion
    Orchestrator->>AgentB: Request Opinion
    Orchestrator->>AgentC: Request Opinion
    
    AgentA->>Orchestrator: Opinion A
    AgentB->>Orchestrator: Opinion B
    AgentC->>Orchestrator: Opinion C
    
    Note left of Orchestrator: Analyze opinions and reach consensus
    Orchestrator->>AgentA: Consensus Decision
    Orchestrator->>AgentB: Consensus Decision
    Orchestrator->>AgentC: Consensus Decision
```

These interaction patterns provide a foundation for understanding how agents communicate and collaborate in the Agentic
Kernel system. By combining these patterns, complex workflows can be created to solve a wide range of problems.