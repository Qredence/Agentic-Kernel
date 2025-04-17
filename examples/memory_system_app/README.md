# Memory System Mesop App

This example demonstrates how to use the memory system in the Agentic Kernel to store and retrieve information across
interactions. The app allows users to:

1. Search the web for information on a topic
2. Store the search results in memory
3. Retrieve the stored information from memory

## Overview

The memory system in Agentic Kernel enables agents to maintain context across different interactions and build up
knowledge over time. This example showcases a simple workflow where:

- A `WebSurferAgent` searches the web for information
- A `MemoryAgent` stores the search results in memory
- Later, the `MemoryAgent` retrieves the stored information when queried

## Components

The example consists of the following components:

- **MemoryAgent**: An agent that interacts with the memory system, providing capabilities for storing and retrieving
  information.
- **WebSurferAgent**: An agent that performs web searches.
- **MemoryManager**: The core component that manages memory storage and retrieval.
- **Mesop UI**: A web interface for interacting with the agents and memory system.

## Running the Example

To run the example:

1. Ensure you have the Agentic Kernel installed
2. Set up your environment variables (especially `GEMINI_API_KEY` for the web search functionality)
3. Run the following command:

```bash
python -m src.agentic_kernel.memory_mesop_app
```

4. Open your browser to the URL displayed in the console (typically http://localhost:8080)

## Using the App

The app provides two main tabs:

### Search & Memorize

1. Enter a search topic in the input field
2. Click "Search & Store"
3. The app will search the web for information on the topic
4. The search results will be displayed and stored in memory

### Recall from Memory

1. Enter a query in the input field
2. Click "Search Memory"
3. The app will search the memory for information related to the query
4. The retrieved memories will be displayed, including their content and metadata

## How It Works

The app demonstrates the following workflow:

1. **Web Search**: When a user enters a search topic, the app creates a task for the `WebSurferAgent` to search the web
   for information on that topic.

2. **Memory Storage**: After the search is complete, the app creates a task for the `MemoryAgent` to store the search
   results in memory, associating them with the search topic.

3. **Memory Retrieval**: When a user queries the memory, the app creates a task for the `MemoryAgent` to search for
   relevant memories. The memory system uses semantic search to find memories that are relevant to the query, even if
   the query doesn't exactly match the stored text.

## Key Concepts

- **Memory Persistence**: Memories are stored persistently, allowing them to be retrieved across different sessions.
- **Semantic Search**: The memory system uses vector embeddings to find relevant memories based on semantic similarity.
- **Metadata and Tagging**: Memories can be associated with metadata and tags, making them easier to organize and
  retrieve.

## Extending the Example

You can extend this example in several ways:

- Add more agents that contribute to the memory system
- Implement more sophisticated memory retrieval strategies
- Add visualization of memory connections
- Implement memory consolidation to combine related memories