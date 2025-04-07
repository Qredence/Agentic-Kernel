# Agentic Kernel, inspired by Semantic Kernel and Autogen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add other badges: PyPI version, build status, etc. -->

**Supercharge your Microsoft Semantic Kernel applications with AgenticFleet Labs!**

This repository provides a collection of robust, pre-built plugins designed to give your AI agents powerful capabilities with minimal setup. Integrate these plugins easily to enable tasks like web browsing, file system interaction, and more.

## Available Plugins

Easily add sophisticated features to your Semantic Kernel agents:

### 🌐 WebSurfer Plugin (`agentic_kernel.plugins.web_surfer`)

**Enable your agent to access and understand information from the live web.**

* **Web Search:** Perform dynamic web searches using DuckDuckGo to fetch up-to-date information.
  * `web_search(query: str, max_results: int = 5)` -> Returns titles, URLs, snippets.
* **Webpage Summarization:** Extract and summarize the key content from any webpage URL.
  * `summarize_webpage(url: HttpUrl)` -> Returns a concise text summary.

**Quick Start:**

```python
import asyncio
import semantic_kernel as sk
from agentic_kernel.plugins.web_surfer import WebSurferPlugin

async def main():
    kernel = sk.Kernel()
    
    # Import the plugin into the kernel
    web_surfer_plugin = kernel.add_plugin(WebSurferPlugin(), "WebSurfer")

    # --- Example: Search the web ---
    search_query = "Latest advancements in large language models"
    print(f"Searching for: '{search_query}'")
    
    search_function = web_surfer_plugin["web_search"]
    # Note: In SK v1+, invoke needs keyword arguments or a KernelArguments object
    result = await kernel.invoke(search_function, query=search_query, max_results=3) 
    
    print("Search Results:")
    # The result of web_search is a list of Pydantic models, 
    # SK might wrap primitive types or require explicit handling.
    # Assuming direct access or appropriate parsing based on SK version:
    if isinstance(result.value, list): # Check if the result is directly the list
         for item in result.value:
             print(f"- {item.title}: {item.url}")
    else:
         print(f"Raw result: {result}") # Adjust parsing as needed

    # --- Example: Summarize a webpage ---
    page_url = "https://learn.microsoft.com/en-us/semantic-kernel/overview/"
    print(f"\nSummarizing: {page_url}")
    
    summarize_function = web_surfer_plugin["summarize_webpage"]
    summary_result = await kernel.invoke(summarize_function, url=page_url)
    
    print(f"Summary:\n{summary_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 📁 FileSurfer Plugin (`agentic_kernel.plugins.file_surfer`)

**Allow your agent to safely interact with files on the local system within designated boundaries.**

* **List Files:** Browse directories and find files matching specific patterns.
  * `list_files(pattern: str = "*", recursive: bool = False)` -> Returns file details (name, path, size, type, modified date).
* **Read Files:** Extract the content of specific text-based files.
  * `read_file(file_path: str)` -> Returns file content as a string.
* **Search File Content:** Locate files containing specific text.
  * `search_files(text: str, file_pattern: str = "*")` -> Returns list of files where the text was found.

**Important Security Note:** This plugin **must** be initialized with a `base_path` to restrict file operations to a specific directory, preventing unintended access to sensitive areas of the file system.

**Quick Start:**

```python
import asyncio
import semantic_kernel as sk
from pathlib import Path
from agentic_kernel.plugins.file_surfer import FileSurferPlugin

async def main():
    kernel = sk.Kernel()

    # --- Setup: Create a safe directory for the example ---
    safe_dir = Path("./agent_files_example").resolve() # Use resolve() for absolute path
    safe_dir.mkdir(exist_ok=True)
    (safe_dir / "notes.txt").write_text("Meeting notes: Discuss project Alpha.")
    (safe_dir / "report.md").write_text("# Project Beta Report\nStatus: Ongoing.")
    print(f"Created example files in: {safe_dir}")

    # --- Initialize and add the plugin ---
    # CRITICAL: Always define a safe base_path!
    file_surfer = FileSurferPlugin(base_path=safe_dir) 
    file_plugin = kernel.add_plugin(file_surfer, "FS") # Short name 'FS'

    # --- Example: List text files ---
    print("\nListing '.txt' files:")
    list_func = file_plugin["list_files"]
    list_result = await kernel.invoke(list_func, pattern="*.txt")
    if isinstance(list_result.value, list):
        for f in list_result.value:
            print(f"- {f.name} (Modified: {f.last_modified})")
    else:
        print(f"Raw result: {list_result}")


    # --- Example: Read a specific file ---
    print("\nReading 'notes.txt':")
    read_func = file_plugin["read_file"]
    read_result = await kernel.invoke(read_func, file_path="notes.txt")
    print(f"Content:\n{read_result}")

    # --- Example: Search for files containing 'Project' ---
    print("\nSearching for files with 'Project':")
    search_func = file_plugin["search_files"]
    search_result = await kernel.invoke(search_func, text="Project", file_pattern="*.md")
    if isinstance(search_result.value, list):
        for f in search_result.value:
            print(f"- Found in: {f.name}")
    else:
         print(f"Raw result: {search_result}")


    # --- Cleanup: Remove example directory ---
    print("\nCleaning up example files...")
    for item in safe_dir.iterdir():
        item.unlink()
    safe_dir.rmdir()
    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(main())

```

## System Architecture

Agentic Kernel implements a sophisticated multi-agent architecture designed for autonomous task execution and orchestration. This modular system enables flexible agent interactions, secure execution environments, and robust workflow management.

### Core Components

#### 1. Agent System

The agent system provides:
- Modular agent architecture with specialized capabilities
- Dynamic agent registration and discovery
- Configurable agent behaviors
- Secure inter-agent communication
- Resource management and optimization

#### 2. Workflow Engine

The workflow engine handles:
- Intelligent task decomposition and allocation
- Real-time progress tracking
- Sophisticated error handling and recovery
- Concurrent execution support
- Performance metrics collection

#### 3. Communication Protocol

Agents exchange standardized messages in this format:

```json
{
    "message_id": "uuid",
    "sender": "agent_id",
    "receiver": "agent_id",
    "message_type": "task|status|control",
    "content": {},
    "metadata": {
        "timestamp": "iso8601",
        "priority": "number",
        "tags": ["array"]
    }
}
```

#### 4. Orchestrator Agent

The Orchestrator Agent is the central component of the system that manages workflow execution:

- **Dynamic Planning**: Creates, manages, and revises plans for complex tasks
  - Implements nested loop architecture (outer loop for planning, inner loop for execution)
  - Automatically decomposes high-level goals into manageable subtasks
  - Creates natural language plans for task execution
  - Dynamically adapts plans based on execution progress

- **Error Recovery**: Sophisticated mechanisms to handle failures
  - Detects and recovers from execution errors
  - Implements replanning when progress is insufficient
  - Uses reflection to identify blocking issues
  - Applies alternative approaches to failed steps

- **Progress Monitoring**: Continuous evaluation of workflow execution
  - Tracks completion status of individual steps
  - Calculates weighted progress metrics
  - Detects loops and deadlocks
  - Provides detailed execution metrics

- **Task Delegation**: Intelligent assignment of tasks to specialized agents
  - Matches tasks to agent capabilities
  - Manages dependencies between tasks
  - Coordinates parallel or sequential execution
  - Resets agent states during replanning

The Orchestrator's nested loop architecture allows for:
1. **Outer Loop**: Task ledger management and planning/replanning
2. **Inner Loop**: Progress ledger management and step execution
3. **Reflection**: Evaluation when progress falls below thresholds

### Chainlit Integration

Agentic Kernel includes a Chainlit-based user interface that provides:

- Real-time interaction with the agent system
- Task tracking and visualization
- Support for multiple AI models through profiles
- Integration with external tool providers (MCP)
- Streaming responses for immediate feedback
- Automatic detection of complex tasks for orchestration

**Quick Start with Chainlit:**

```bash
# Install the package
uv pip install agentic-kernel

# Run the Chainlit app
chainlit run src/agentic_kernel/app.py
```

This will start a web interface where you can interact with the agent system, monitor workflows, and visualize the execution of complex tasks.

## Installation

Get started with AgenticFleet Labs plugins in your project quickly.

**Prerequisites:**

*   Python 3.10+
*   An existing Python project with Semantic Kernel installed.
*   `uv` (recommended) or `pip` package manager.
*   Environment variables set for necessary services (e.g., `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`). See `.env.example`.

**Using `uv` (Recommended):**

1.  **Install `uv`:**
    ```bash
    pip install uv
    # Or follow instructions at https://github.com/astral-sh/uv
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    uv venv
    source .venv/bin/activate
    ```
3.  **Install dependencies from `pyproject.toml`:**
    ```bash
    uv pip install -r requirements.txt # Or sync directly with pyproject.toml if using uv's management features
    # Alternatively, if installing this package itself:
    # uv pip install .
    ```

**Using `pip`:**

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```
2.  **Install:**
    ```bash
    pip install -r requirements.txt # Or pip install agentic-kernel (if published)
    ```

## Running the Application

The primary way to run the application is using the Chainlit web interface.

1.  **Ensure dependencies are installed** (see Installation).
2.  **Make sure your virtual environment is active** (`source .venv/bin/activate`).
3.  **Set required environment variables** (copy `.env.example` to `.env` and fill in your credentials).
4.  **Run the Chainlit app:**

    *   **Using the provided script:**
        ```bash
        ./scripts/run_chainlit.sh
        ```
        This script handles activating the environment (if needed) and setting the `PYTHONPATH`.

    *   **Manually with Chainlit:**
        ```bash
        chainlit run src/agentic_kernel/app.py -w
        ```
        (The `-w` flag enables auto-reloading on code changes.)

5.  **Access the application** in your web browser (usually at `http://localhost:8000`).

### Debugging Scripts

*   `src/simple_debug.py`: A minimal Chainlit app useful for testing specific components in isolation. Run with `chainlit run src/simple_debug.py -w`.
*   `src/debug_app.py`: A command-line script to quickly validate imports and basic component initialization. Run with `python src/debug_app.py`.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Need Help?

If you encounter issues or have questions, please file an issue on the [GitHub repository](https://github.com/AgenticFleet/AgenticFleet-Labs/issues).
