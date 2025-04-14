# Basic Workflow Example

This example demonstrates how to create and execute a simple workflow using Agentic Kernel.

## Scenario

In this example, we'll create a workflow that:
1. Fetches data from a web API
2. Processes the data
3. Saves the results to a file

## Implementation

```python
from agentic_kernel import AgentSystem, Workflow
from agentic_kernel.agents import WebAgent, FileAgent
from typing import Dict, List

# Initialize the system
system = AgentSystem()

# Register required agents
web_agent = WebAgent()
file_agent = FileAgent()
system.register_agents([web_agent, file_agent])

# Define tasks
@Workflow.task
def fetch_data(url: str) -> Dict:
    """Fetch data from an API endpoint"""
    return web_agent.get(url)

@Workflow.task
def process_data(data: Dict) -> List:
    """Process the fetched data"""
    # Example processing
    return [item for item in data['items'] if item['status'] == 'active']

@Workflow.task
def save_results(processed_data: List, output_path: str):
    """Save the processed data to a file"""
    file_agent.write_json(output_path, processed_data)

# Create the workflow
workflow = Workflow("data-processing")
workflow.add_tasks([
    (fetch_data, {"url": "https://api.example.com/data"}),
    (process_data, {}),  # Input will be output from fetch_data
    (save_results, {"output_path": "results.json"})
])

# Execute the workflow
try:
    result = system.execute(workflow)
    print("Workflow completed successfully!")
except Exception as e:
    print(f"Workflow failed: {e}")
```

## Key Concepts Demonstrated

1. **Agent Registration**
   - Multiple agents working together
   - Specialized agent capabilities

2. **Task Definition**
   - Task decoration
   - Type hints
   - Clear function purposes

3. **Workflow Construction**
   - Sequential task addition
   - Automatic data passing
   - Parameter specification

4. **Error Handling**
   - Try-catch block
   - Graceful failure handling

## Running the Example

1. Save the code in a file (e.g., `data_workflow.py`)
2. Ensure all dependencies are installed
3. Run the script:
   ```bash
   python data_workflow.py
   ```

## Expected Output

```
Workflow completed successfully!
```

The processed data will be saved in `results.json`.

## Variations

### 1. Adding Parallel Processing

```python
# Modify the workflow to process data in parallel
workflow = Workflow("parallel-processing")
workflow.add_parallel_tasks([
    (process_data, {"chunk": chunk}) for chunk in data_chunks
])
```

### 2. Adding Error Recovery

```python
@Workflow.task(retries=3)
def fetch_data_with_retry(url: str) -> Dict:
    """Fetch data with retry mechanism"""
    return web_agent.get(url)
```

## Next Steps

- Try modifying the example to handle different data sources
- Add more complex processing logic
- Implement custom error handling
- Explore parallel task execution 