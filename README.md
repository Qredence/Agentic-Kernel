# AgenticFleet Labs

A collection of intelligent agents and plugins for Semantic Kernel, designed to enhance your AI applications with powerful capabilities.

## Features

### WebSurfer Plugin

The WebSurfer plugin provides web search and webpage summarization capabilities:

- `web_search(query: str, max_results: int = 5)`: Performs a web search using DuckDuckGo and returns relevant results
- `summarize_webpage(url: HttpUrl)`: Fetches and summarizes the content of a webpage

Example usage:
```python
from agenticfleet.plugins.web_surfer import WebSurferPlugin

# Initialize the plugin
web_surfer = WebSurferPlugin()

# Search the web
results = web_surfer.web_search("semantic kernel plugins")
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Snippet: {result.snippet}")
    print(f"Source: {result.source}\n")

# Summarize a webpage
summary = web_surfer.summarize_webpage("https://example.com")
print(f"Summary: {summary}")
```

### FileSurfer Plugin

The FileSurfer plugin provides file system operations with safety features:

- `list_files(pattern: str = "*", recursive: bool = False)`: Lists files in a directory matching a pattern
- `read_file(file_path: str)`: Reads and returns the content of a file
- `search_files(text: str, file_pattern: str = "*")`: Searches for files containing specific text

Example usage:
```python
from pathlib import Path
from agenticfleet.plugins.file_surfer import FileSurferPlugin

# Initialize the plugin with a base path for safety
file_surfer = FileSurferPlugin(base_path=Path("/safe/directory"))

# List files
files = file_surfer.list_files(pattern="*.txt", recursive=True)
for file in files:
    print(f"Name: {file.name}")
    print(f"Path: {file.path}")
    print(f"Size: {file.size} bytes")
    print(f"Type: {file.content_type}")
    print(f"Modified: {file.last_modified}\n")

# Read a file
content = file_surfer.read_file("document.txt")
print(f"Content: {content}")

# Search files
matching_files = file_surfer.search_files("important", file_pattern="*.txt")
for file in matching_files:
    print(f"Found in: {file.name}")
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AgenticFleet/AgenticFleet-Labs.git
cd AgenticFleet-Labs
```

2. Install the package with all dependencies:
```bash
pip install -e ".[test,dev]"
```

## Development

1. Set up the development environment:
```bash
# Install development dependencies
pip install -e ".[test,dev]"

# Install pre-commit hooks
pre-commit install
```

2. Run tests:
```bash
pytest
```

3. Run linters:
```bash
# Format code
black .
isort .

# Check types
mypy .

# Run linter
ruff check .
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
