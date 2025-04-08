# Guide: Using the Chainlit User Interface

The Agentic Kernel can be integrated with Chainlit to provide an interactive chat-based user interface for defining goals, running workflows, and monitoring progress.

## Prerequisites

*   Python environment set up for the Agentic Kernel project.
*   Dependencies installed (including `chainlit`).
*   Any necessary API keys or configurations set in your environment (e.g., `.env` file).

## Running the Chainlit UI

To start the application with the Chainlit interface, you typically run a specific Python script that initializes both the Agentic Kernel components (like the Orchestrator) and the Chainlit application.

1.  **Identify the Entry Point:** Find the Python script designated as the Chainlit entry point. This might be `app.py`, `main.py`, `chainlit_app.py`, or similar within the `src` or root directory.
    *   *Self-correction: Based on previous context, a file like `src/agentic_kernel/app.py` or a dedicated file in `src/agentic_kernel/ui/` might exist.* Let's assume `src/agentic_kernel/ui/chainlit_app.py` is the entry point for this guide.

2.  **Navigate to the Project Root:** Open your terminal and change the directory to the root of the `agentic-kernel` project.

3.  **Run the Chainlit Command:** Execute the Chainlit run command, pointing it to your entry point script.
    ```bash
    # Ensure you are in the project root directory
    # Make sure your virtual environment (e.g., .venv created by uv) is active
    
    chainlit run src/agentic_kernel/ui/chainlit_app.py -w
    ```
    *   `chainlit run`: The command to start a Chainlit application.
    *   `src/agentic_kernel/ui/chainlit_app.py`: The path to the Python file containing your Chainlit app logic (adjust the path if necessary).
    *   `-w` (or `--watch`): Optional flag that automatically reloads the app when you save changes to the source file, useful for development.

4.  **Access the UI:** Chainlit will typically print a local URL to the console (e.g., `http://localhost:8000`). Open this URL in your web browser.

## Interacting with the UI

Once the Chainlit interface loads, you'll likely see a chat window. The exact interaction flow depends on how the `chainlit_app.py` script is implemented, but common patterns include:

1.  **Starting a Workflow:**
    *   You might be prompted to enter a goal or task description in the chat input.
    *   Type your desired goal (e.g., "Research the latest AI trends and save findings to a file named ai_trends.md").
    *   Press Enter or click the send button.

2.  **Monitoring Progress:**
    *   The application should display messages indicating the start of the workflow.
    *   As the Orchestrator executes steps, the UI might show updates:
        *   Which step is currently running.
        *   Which agent is performing the task.
        *   Intermediate results or status messages.
        *   Any errors encountered.
    *   Look for visual cues like loading indicators or step breakdowns provided by the Chainlit app's design.

3.  **Viewing Results:**
    *   Upon completion, the UI should display the final status (e.g., "Workflow completed successfully" or "Workflow failed").
    *   The final results or a summary might be presented in the chat.
    *   If the workflow generated artifacts (like files), the UI might provide information about them or links if applicable.

4.  **Handling Errors:**
    *   If a step fails and cannot be recovered, the UI should clearly indicate the failure and provide details about the error if possible.

## Example Interaction

```
> User: Summarize the key points from the website https://agentickernel.dev/docs

< App: Okay, starting workflow to summarize the webpage...
< App: [Step 1/2] WebSurferAgent: Fetching content from https://agentickernel.dev/docs
< App: [Step 2/2] SummarizerAgent: Generating summary...
< App: Workflow completed successfully!
< App: Summary:
The Agentic Kernel documentation covers core concepts like the Orchestrator, Agents, Memory, and Plugins. It provides guides for getting started and examples for various features...

> User: 
```

## Stopping the Application

*   Go back to the terminal where you ran the `chainlit run` command.
*   Press `Ctrl + C` to stop the Chainlit server. 