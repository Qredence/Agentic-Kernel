# Agentic Kernel CLI Workflow Demo

This example demonstrates how to use the Agentic Kernel library to create a command-line interface for executing multi-agent workflows. It showcases the orchestration capabilities of the library, allowing you to run complex tasks using multiple specialized agents.

## Features

- Command-line interface for executing workflows
- Support for multiple agent types:
  - WebSurfer: Web search and content retrieval
  - FileSurfer: File system operations
  - Coder: Code generation and analysis
  - Terminal: Secure command execution
- Workflow orchestration with progress tracking
- Rich console output with status updates
- Configurable agent selection
- Working directory support
- Detailed metrics reporting

## Prerequisites

- Python 3.10 or higher
- Agentic Kernel library
- Azure OpenAI API access (for LLM capabilities)

## Installation

1. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Usage

The CLI provides a simple interface to execute workflows:

```bash
# Execute a workflow with all available agents
agentic-workflow "Search for Python articles and save summaries to files"

# Execute with specific agents
agentic-workflow "Generate test cases for my code" --agents code file

# Execute in a specific working directory
agentic-workflow "Analyze log files" --working-dir /path/to/logs
```

### Command Options

- `task`: The task description (required)
- `--working-dir, -d`: Set the working directory for file operations
- `--agents, -a`: Specify which agents to use (comma-separated)

### Example Tasks

1. Web research and summarization:
   ```bash
   agentic-workflow "Research latest AI trends and create a summary report"
   ```

2. Code analysis and generation:
   ```bash
   agentic-workflow "Analyze Python files in current directory and suggest improvements"
   ```

3. File operations:
   ```bash
   agentic-workflow "Organize files by type and create a report" -d ./documents
   ```

4. Combined operations:
   ```bash
   agentic-workflow "Find security best practices online and update our configuration files"
   ```

## Configuration

The application uses the Agentic Kernel configuration system. You can customize:

- Agent configurations
- LLM settings
- Security policies
- Logging preferences

## Contributing

Feel free to submit issues and enhancement requests! 