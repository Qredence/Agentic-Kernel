<!-- Optional: Add a project logo/banner here -->
<!-- <p align="center"><img src="path/to/your/logo.png" alt="Agentic Kernel Logo" width="200"/></p> -->

# Agentic Kernel: A Modular Framework for Autonomous AI Agents


<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/agentic-kernel.svg)](https://badge.fury.io/py/agentic-kernel)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

**Build, orchestrate, and manage sophisticated multi-agent systems with ease.**
---


Agentic Kernel provides a robust and flexible foundation for creating A2A-compatible autonomous AI agents that can collaborate, reason, and execute complex tasks through standardized agent-to-agent communication protocols. 
Built on Google's A2A standard at its core, and leveraging the ADK (Agent Development Kit) framework, it implements key interoperability features like capability discovery, consensus building, and collaborative memory while offering a modular architecture, dynamic workflow management, and seamless integration capabilities.

## ✨ Key Features

* **🤖 Modular Multi-Agent Architecture:** 
Design systems with specialized agents, dynamic registration, and secure communication.
  
* **⚙️ Sophisticated Workflow Engine:** 
Intelligently decompose tasks, track progress in real-time, handle errors gracefully, and manage concurrent execution.
  
* **🧠 Dynamic Planning & Orchestration:** 
Features a powerful Orchestrator Agent capable of creating, managing, and adapting complex plans using a nested loop architecture.
  
* **🔌 Pluggable Components:** 
Easily extend functionality with custom plugins, tools, and memory systems.
  
* **💬 Standardized Communication:** Agents interact using a clear and consistent message format, compliant with
  Google's [A2A (Agent-to-Agent) interoperability standard](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/).
  
* **🖥️ Interactive UI:** Includes a Chainlit-based interface for real-time interaction, task visualization, and
  monitoring.
  
* **🛠️ Rich Tooling & Integration:** Leverage built-in tools and integrate with external systems (e.g., via MCP).


## 🚀 Getting Started

Follow these steps to get Agentic Kernel up and running on your local machine.

**Prerequisites:**

* Python 3.10 or higher
* `uv` (recommended) or `pip` package manager
* Git (for cloning the repository)

**Installation & Setup:**

1. **Clone the Repository (if you haven't already):**
    ```bash
    git clone https://github.com/qredence/agentic-kernel.git
    cd agentic-kernel
    ```

2. **Create and Activate a Virtual Environment:**

    * **Using `uv` (Recommended):**
      ```bash
      # Install uv if you don't have it (e.g., pip install uv)
      uv venv
      source .venv/bin/activate
      ```
    * **Using standard `venv`:**
      ```bash
      python -m venv .venv
      source .venv/bin/activate # On Windows use: .venv\Scripts\activate
      ```

3. **Install Dependencies:**
    ```bash
    # Using uv
    uv sync
    ```

4. **Configure Environment Variables:**
    * Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    * Edit the `.env` file and add your API keys and endpoints for required services (e.g., Azure OpenAI, specific
      tools).

**Running the [A2A Agents Orchestrations (ADK Chat)](./src/agentic_kernel/adk_chat/README.md):**

1. **Ensure your virtual environment is active.**

    ```bash
    # Using uv
    uv venv
    source .venv/bin/activate
    ``` 
    

## Setup

1. **Install Dependencies:** From the workspace root (`Agentic-Kernel`), install the required packages:
   ```bash
   uv pip install -r src/agentic_kernel/adk_chat/requirements.txt
   ```

2. **Configure Environment Variables:** Ensure you have the necessary API keys set in your `.env` file (or the specific `.env` within the `adk_chat` directory if you prefer):
   ```
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_API_KEY=your_google_api_key
   ```

## Running the Example

From the workspace root (`Agentic-Kernel`), run:

```bash
python src/agentic_kernel/adk_chat/main.py
```

This will start the chat server and client, allowing you to interact with the multi-agent system.

### Running with Mesop UI

You can also run the system with a web-based UI using Mesop:

```bash
python src/agentic_kernel/adk_chat/main.py --mode mesop
```

This will start the server and launch the Mesop UI in your default web browser. The UI provides a more user-friendly
interface for interacting with the multi-agent system, with features like:

- Agent information display
- Chat history with markdown formatting
- Message input with real-time feedback
- Visual indicators for processing state

## 🏛️ System Architecture

Agentic Kernel employs a modular design centered around interacting components:

```
src/agentic_kernel/
├── agents/         # Specialized agent implementations (e.g.,    Orchestrator, Worker)
├── communication/  # Protocols and message formats for inter-agent communication
├── config/        # Configuration loading and management
├── ledgers/       # State tracking for tasks and progress
├── memory/        # Systems for agent memory and knowledge storage
├── orchestrator/  # Core logic for workflow planning and execution
├── plugins/       # Extensible plugin system for adding capabilities
├── systems/       # Foundational system implementations
├── tools/         # Reusable tools agents can leverage
├── ui/           # User interface components (e.g., Chainlit app)
├── utils/        # Helper functions and utilities
├── workflows/     # Definitions and handlers for specific workflows
└── adk_chat/      # ADK A2A Chat System
```

### A2A Compliance

Agentic Kernel is compliant with
Google's [A2A (Agent-to-Agent) interoperability standard](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/),
which enables seamless communication and collaboration between different agent systems. Key A2A features include:

- **Capability Discovery**: Agents can advertise their capabilities and discover the capabilities of other agents.
- **Agent Discovery**: Agents can announce their presence and find other agents in the system.
- **Standardized Message Format**: All agent communication follows a consistent format with required A2A fields.
- **Consensus Building**: Agents can request and build consensus on decisions.
- **Conflict Resolution**: The system provides mechanisms for detecting and resolving conflicts between agents.
- **Task Decomposition**: Complex tasks can be broken down into subtasks and distributed among agents.
- **Collaborative Memory**: Agents can share and access a common memory space.

To test A2A compliance, run the provided test script:

```bash
python src/debug/test_a2a_compliance.py
```

### Core Concepts

* **Agents:** Autonomous units with specific capabilities (e.g., planning, executing, validating). The
  `OrchestratorAgent` is key for managing complex tasks.
* **Workflows:** Sequences of steps managed by the Workflow Engine, involving task decomposition, execution, and
  monitoring.
* **Communication Protocol:** A standardized JSON format for messages exchanged between agents.
* **Ledgers:** Track the state and progress of tasks and workflows.
* **Plugins & Tools:** Extend agent functionality by providing access to external capabilities or data.

Refer to the code documentation within each directory for more detailed information.

## 📚 Examples & Usage

Explore the capabilities of Agentic Kernel through practical examples:

* **Core Feature Examples (`docs/examples/`)**: Detailed markdown files demonstrating specific functionalities like:
    * Advanced Plugin Usage
    * Agent Communication Patterns
    * Basic Workflow Definition
    * Memory System Interaction
    * Orchestrator Features (Conditional Steps, Dynamic Planning, Error Recovery)
    * Workflow Optimization

* **Multi-Agent System (`examples/adk_multi_agent/`)**: A complete example showcasing collaboration between multiple
  agents (Task Manager, Worker, Validator).
    * See the [Multi-Agent Example README](examples/adk_multi_agent/README.md) for setup and execution instructions.

* **ADK A2A Chat System (`src/agentic_kernel/adk_chat/`)**: A multi-agent chat system using Google's Agent Development Kit (
  ADK) and Agent-to-Agent (A2A) communication protocol.
    * Features specialized agents (Orchestrator, Research, Creative, Reasoning) that communicate using the A2A protocol
    * Includes both a command-line interface and a web-based UI using Mesop
    * See the [ADK A2A Chat README](src/agentic_kernel/adk_chat/README.md) for setup and execution instructions

## 🤝 Contributing

We welcome contributions! Please read our `CONTRIBUTING.md` guide to learn about our development process, how to propose
bug fixes and improvements, and coding standards.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🐛 Debugging

* The `src/debug/` directory contains scripts useful for isolating and testing specific components of the kernel.
  Explore these scripts if you encounter issues or want to understand individual parts better.
