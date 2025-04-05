# Agentic Kernel Chainlit Demo

This example demonstrates how to use the Agentic Kernel library with Chainlit to create an interactive chat application with dynamic tool support.

## Features

- Interactive chat interface powered by Chainlit
- Dynamic tool registration and management
- Support for multiple chat profiles (Fast and Max)
- Integration with Azure OpenAI for LLM capabilities
- Built-in support for WebSurfer and FileSurfer plugins
- Database integration with Neon

## Prerequisites

- Python 3.10 or higher
- Azure OpenAI API access
- Neon database account (optional)

## Setup

1. Clone the repository and navigate to the example directory:
   ```bash
   cd examples/chainlit_app
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Create a `.env` file with your configuration:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key
   AZURE_OPENAI_ENDPOINT=your_endpoint
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   NEON_MCP_TOKEN=your_neon_token  # Optional
   ```

## Running the Application

Start the Chainlit application:
```bash
chainlit run src/agentic_kernel_demo/app.py
```

The application will be available at `http://localhost:8000`.

## Usage

1. Select a chat profile (Fast or Max) based on your needs
2. Start chatting with the AI assistant
3. The assistant will automatically use available tools based on your queries
4. For database operations, use the "list_tables" action to view available tables

## Configuration

You can customize the application by modifying:

- Chat profiles in `app.py`
- Model deployments in `DEPLOYMENT_NAMES`
- Logging configuration
- Plugin settings

## Contributing

Feel free to submit issues and enhancement requests! 