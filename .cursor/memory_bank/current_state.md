# AgenticFleet-Labs Current State

## Project Structure

```
/AgenticFleet-Labs
├── .chainlit/               # Chainlit configuration
│   ├── config.toml         # UI and feature settings
│   └── translations/       # Optional i18n support
├── src/
│   └── agenticfleet/      # Main package source
│       ├── __init__.py
│       ├── plugins/         # Semantic Kernel plugins (replaces agents/)
│       │   ├── __init__.py
│       │   └── weather_plugin.py # Example initial plugin
│       ├── config/          # Configuration files
│       │   └── llm_config.json # LLM endpoints and settings for SK Connectors
│       ├── workflows/       # Agent interaction patterns (Potentially less emphasis with SK Planner)
│       │   └── __init__.py
│       └── utils/           # Helper functions
│           └── __init__.py
├── tests/                 # Test suite (TDD approach)
│   ├── __init__.py
│   ├── plugins/         # Tests for SK plugins
│   │   ├── __init__.py
│   │   └── test_weather_plugin.py
│   ├── workflows/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── .env                   # Environment variables (ignored by git)
├── .gitignore             # Files ignored by git
├── app.py                 # Main Chainlit application entry using Semantic Kernel
├── pyproject.toml         # Project config, dependencies, build settings
└── README.md              # Project documentation
```

## Configuration Files

### pyproject.toml

- Dependencies: `semantic-kernel`, `semantic-kernel[azure]` (includes connectors), `chainlit`, `pydantic`, `python-dotenv`
- Test dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`
- Dev dependencies: `black`, `isort`, `mypy`, `ruff`
- Build system: `hatchling`

### .chainlit/config.toml

- Enabled features: MCP, chat settings, chat profiles
- Linked to GitHub repo

### src/config/llm_config.json

- Structure for defining LLM endpoints and parameters for Semantic Kernel Connectors.
- Needs to store API keys (preferably via env vars), model IDs, potentially endpoint URLs for Azure.

## Recent Changes

### Streaming Implementation (`app.py`)

- Implemented proper async streaming using Semantic Kernel's `get_streaming_chat_message_content`
- Added structured logging with different log levels (INFO, WARNING, ERROR)
- Improved error handling with detailed error messages and stack traces
- Added proper type hints for async generators
- Fixed async context manager protocol issues

### Logging Improvements

- Added basic logging configuration with timestamp and log levels
- Implemented logging for critical operations:
  - Chat session initialization
  - Service initialization failures
  - Message processing errors
  - Environment variable issues
- Added secure logging practices (no sensitive data)

### Type System Improvements

- Added AsyncGenerator type hints
- Improved documentation with Args, Yields, and Raises sections
- Added optional type hints for configuration loader

## Current Implementation State

### Core Framework: Semantic Kernel + Chainlit (`app.py`)

- The primary interaction logic resides in `app.py`
- **Chainlit Integration:** 
  - Utilizes proper streaming with Semantic Kernel
  - Handles message chunks correctly
  - Provides real-time updates to UI
- **Kernel Initialization (`@cl.on_chat_start`):**
  - Creates `sk.Kernel()`
  - Adds AI services with proper error handling
  - Configures logging
  - Stores components in session with type hints
- **Message Handling (`@cl.on_message`):**
  - Uses proper async streaming patterns
  - Implements structured error handling
  - Provides detailed logging
  - Maintains chat history correctly

### Plugins (To be created in `src/agenticfleet/plugins/`)

- Agent capabilities (WebSurfer, FileSurfer, Coder, TaskPlanner) will be implemented as Semantic Kernel plugins.
- Each plugin will contain Python classes with methods decorated using `@kernel_function`.
- Currently, only the placeholder `WeatherPlugin` exists within `app.py`.

### Tests (To be created in `tests/plugins/` and `tests/` for `app.py`)

- Unit tests will focus on validating the logic within each plugin's kernel functions, mocking external dependencies and SK context where necessary.
- Tests for `app.py` will verify kernel setup and message handling flow (mocking SK calls).

## Development Rules

1. Test-Driven Development (TDD) approach
   - Write tests for plugins first.
   - Write plugin code until tests pass.
   - Write tests for `app.py` integration points.
   - Implement `app.py` logic.
   - Write documentation.
2. Package Dependencies
   - Use `semantic-kernel` and specific `semantic-kernel-connectors-*` packages (or extras like `[azure]`).
   - Use latest Chainlit version.
   - Avoid legacy `autogen-*` packages unless a specific, justified need arises later.
3. Package Management
   - Always use `uv` for Python package operations.
   - Never use plain `pip` commands.

## Next Steps

1. ~~**Setup:** Add Semantic Kernel dependencies (`semantic-kernel`, connectors).~~ (Done)
2. ~~**Basic App:** Implement basic `app.py` structure using `cl.SemanticKernelFilter`.~~ (Done)
3. **Testing (Basic):** Write initial tests for `app.py` setup and placeholder plugin.
4. **Plugin Dev:** Develop core agent plugins (WebSurfer, FileSurfer, Coder, TaskPlanner) using TDD in `src/agenticfleet/plugins/`.
5. **LLM Config:** Refine `llm_config.json` and kernel setup to handle multiple LLM services (Gemini, etc.) via SK connectors.
6. **Orchestration:** Configure SK's function calling/planning (`FunctionChoiceBehavior`) to orchestrate plugin usage.
7. **Refinement:** Iterate on prompts, plugin logic, and error handling.
