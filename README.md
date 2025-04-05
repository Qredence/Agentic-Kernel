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

## Installation

Get started with AgenticFleet Labs plugins in your project quickly.

**Prerequisites:**

* Python 3.10+
* An existing Python project with Semantic Kernel installed.
* `pip` or `uv` (recommended) package manager.

**Steps:**

1. **Install the package:**
    * Using `pip`:

        ```bash
        pip install agentic-kernel 
        ```

        *(Note: Replace `agentic-kernel` with the actual package name on PyPI once published)*
    * Using `uv`:

        ```bash
        uv pip install agentic-kernel 
        ```

        *(Note: Replace `agentic-kernel` with the actual package name on PyPI once published)*

    * **For development/local use:** If you've cloned the repository (`git clone ...`), you can install it in editable mode from the project directory:

        ```bash
        # Activate your project's virtual environment first!
        # Using pip:
        pip install -e . 
        # Using uv:
        uv pip install -e . 
        ```

2. **Import and use** the plugins in your Semantic Kernel application as shown in the examples above.

## Contributing & Development

Interested in contributing to AgenticFleet Labs or developing the plugins further? We welcome your help!

**Quick Setup for Development:**

1. **Clone:** `git clone https://github.com/AgenticFleet/AgenticFleet-Labs.git && cd AgenticFleet-Labs`
2. **Environment:** `uv venv && source .venv/bin/activate` (or use standard `python -m venv .venv`)
3. **Install Dev Dependencies:** `uv pip install -e ".[test,dev]"` (or `pip install -e ".[test,dev]"`)
4. **Install Hooks:** `pre-commit install`

**Key Development Tasks:**

* **Run Tests:** `uv run pytest` (or `pytest`)
* **Format & Lint:** `uv run ruff format . && uv run ruff check --fix .` (or use `ruff` directly)
* **Type Check:** `uv run mypy .` (or `mypy .`)

Please refer to our [Contribution Guidelines](CONTRIBUTING.md) (link to be created) for more details on the development process, coding standards, and submitting pull requests. We also use `tasks.md` to track ongoing work.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Need Help?

If you encounter issues or have questions, please file an issue on the [GitHub repository](https://github.com/AgenticFleet/AgenticFleet-Labs/issues).
