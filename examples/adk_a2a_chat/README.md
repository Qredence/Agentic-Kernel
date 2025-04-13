# ADK A2A Chat System

This example demonstrates a multi-agent chat system using Google's Agent Development Kit (ADK), Agentic-Kernel, and
Agent-to-Agent (A2A) communication protocol for orchestration.

## Features

- **Chat Interface**: A simple chat interface for interacting with the multi-agent system
- **Multiple Specialized Agents**: Several agents with different roles and capabilities
    - **Orchestrator Agent**: Coordinates the conversation and delegates tasks to specialized agents
    - **Research Agent**: Retrieves and summarizes information
    - **Creative Agent**: Generates creative content
    - **Reasoning Agent**: Performs logical reasoning and analysis
- **A2A Communication**: Agents communicate using the A2A protocol
- **ADK Integration**: Agents are built using Google's Agent Development Kit
- **Agentic-Kernel Components**: Leverages coordination, trust, and other components from Agentic-Kernel

## Architecture

The system follows a hub-and-spoke architecture:

1. The Orchestrator Agent acts as the central hub, receiving user messages and coordinating responses
2. Specialized agents act as spokes, handling specific tasks delegated by the Orchestrator
3. All communication between agents uses the A2A protocol
4. The Agentic-Kernel provides coordination, trust, and other services

```
                  ┌─────────────┐
                  │   User      │
                  └──────┬──────┘
                         │
                         ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Research   │◄───┤Orchestrator │───►│  Creative   │
│   Agent     │    │   Agent     │    │   Agent     │
└─────────────┘    └──────┬──────┘    └─────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  Reasoning  │
                  │   Agent     │
                  └─────────────┘
```

## Structure

```
adk_a2a_chat/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── research.py
│   ├── creative.py
│   └── reasoning.py
├── server/
│   ├── __init__.py
│   └── chat_server.py
├── client/
│   ├── __init__.py
│   └── chat_client.py
├── ui/
│   ├── __init__.py
│   └── mesop_ui.py
├── utils/
│   ├── __init__.py
│   └── adk_a2a_utils.py
├── __init__.py
├── main.py
├── requirements.txt
└── README.md
```

## Setup

1. **Install Dependencies:** From the workspace root (`Agentic-Kernel`), install the required packages:
   ```bash
   uv pip install -r examples/adk_a2a_chat/requirements.txt
   ```

2. **Configure Environment Variables:** Ensure you have the necessary API keys set in your `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_API_KEY=your_google_api_key
   ```

## Running the Example

From the workspace root (`Agentic-Kernel`), run:

```bash
python examples/adk_a2a_chat/main.py
```

This will start the chat server and client, allowing you to interact with the multi-agent system.

### Running with Mesop UI

You can also run the system with a web-based UI using Mesop:

```bash
python examples/adk_a2a_chat/main.py --mode mesop
```

This will start the server and launch the Mesop UI in your default web browser. The UI provides a more user-friendly
interface for interacting with the multi-agent system, with features like:

- Agent information display
- Chat history with markdown formatting
- Message input with real-time feedback
- Visual indicators for processing state

## Implementation Details

### A2A Integration

The system uses the A2A protocol for all agent communication:

- Each agent exposes its capabilities through an A2A server
- Agents discover and communicate with each other using A2A clients
- Task delegation and results are communicated using A2A tasks

### ADK Integration

Agents are implemented using Google's Agent Development Kit:

- Each agent is an instance of `google.adk.agents.Agent`
- Agents use ADK tools to expose their capabilities
- The ADK session service manages agent state

### Agentic-Kernel Integration

The system leverages several components from Agentic-Kernel:

- Coordination Manager for task state management
- Trust Manager for agent trust scores
- A2A implementation for agent communication
