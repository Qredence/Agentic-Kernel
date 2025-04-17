"""Memory System Mesop App.

This module implements a Mesop app that demonstrates the memory system capabilities
of the Agentic Kernel. It allows users to:
1. Search the web for information on a topic
2. Store the search results in memory
3. Retrieve the stored information from memory

The app showcases how agents can maintain context across different interactions
and build up knowledge over time.

Typical usage:
    ```python
    # Run the Mesop app
    python -m src.agentic_kernel.memory_mesop_app
    ```

Dependencies:
    - mesop: For UI and chat interface
    - agentic_kernel: For AI model and memory integration
    - python-dotenv: For environment variable management
"""

import logging
import os

import mesop as mp
from dotenv import load_dotenv
from mesop.components import (
    button,
    container,
    markdown,
    tab,
    tabs,
    text_input,
)

# Import core components
from agentic_kernel.agents.memory_agent import MemoryAgent
from agentic_kernel.agents.web_surfer_agent import WebSurferAgent
from agentic_kernel.config import (
    AgentConfig,
    AgentTeamConfig,
    ConfigLoader,
    LLMMapping,
)
from agentic_kernel.ledgers.progress_ledger import ProgressLedger
from agentic_kernel.ledgers.task_ledger import TaskLedger
from agentic_kernel.memory.manager import MemoryManager
from agentic_kernel.types import Task
from agentic_kernel.utils.task_manager import TaskManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
logger.info(".env file loaded (if exists).")

# Check for Gemini API Key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    logger.warning("GEMINI_API_KEY environment variable not set.")
else:
    logger.info("GEMINI_API_KEY found.")

# --- Constants ---
deployment_names = {"Fast": "gemini-1.5-flash", "Max": "gemini-1.5-pro"}
default_deployment = deployment_names.get("Fast", "gemini-1.5-flash")

# --- Core Initialization ---
try:
    config_loader = ConfigLoader()
    config = config_loader.config
    logger.info("Application configuration loaded.")
except Exception as e:
    logger.critical(f"Failed to load application configuration: {e}", exc_info=True)
    config_loader = ConfigLoader(validate=False)
    config = config_loader.config
    logger.warning("Using fallback application configuration.")

# Initialize task and progress ledgers
task_ledger = TaskLedger()
progress_ledger = ProgressLedger()

# Initialize task manager
task_manager = TaskManager(task_ledger, progress_ledger)
logger.info("TaskManager initialized with task and progress ledgers.")

# Initialize memory manager
memory_manager = MemoryManager(agent_id="memory_system_app")
logger.info("MemoryManager initialized.")

# Initialize agent system
agent_system = {
    "config_loader": config_loader,
    "task_manager": task_manager,
    "memory_manager": memory_manager,
}

# Set up default team configuration if not already configured
if not config_loader.config.default_team:
    logger.info("Setting up default team configuration...")
    default_team = AgentTeamConfig(
        team_name="memory_team",
        description="Team for memory system demo",
        agents=[
            AgentConfig(
                name="web_surfer",
                type="WebSurferAgent",
                description="Agent for web searches",
                llm_mapping=LLMMapping(
                    model=default_deployment,
                    endpoint="gemini",
                    temperature=0.7,
                    max_tokens=2000,
                ),
            ),
            AgentConfig(
                name="memory",
                type="MemoryAgent",
                description="Agent for memory operations",
                llm_mapping=LLMMapping(
                    model=default_deployment,
                    endpoint="gemini",
                    temperature=0.7,
                    max_tokens=2000,
                ),
            ),
        ],
    )
    config_loader.add_agent_team(default_team)
    config_loader.config.default_team = "memory_team"
    logger.info("Default team configuration added successfully.")

# --- Application State ---
class AppState:
    """Application state for the Mesop UI."""
    
    def __init__(self):
        self.search_query = ""
        self.search_results = []
        self.memory_query = ""
        self.memory_results = []
        self.status_message = ""
        self.is_processing = False
        self.web_surfer_agent = None
        self.memory_agent = None
        
    def initialize_agents(self):
        """Initialize the agents."""
        if self.web_surfer_agent is None:
            try:
                self.web_surfer_agent = WebSurferAgent(
                    config=config_loader.get_agent_config("web_surfer"),
                )
                logger.info("WebSurferAgent initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize WebSurferAgent: {e}", exc_info=True)
                self.status_message = f"Error initializing WebSurferAgent: {str(e)}"
                return False
                
        if self.memory_agent is None:
            try:
                self.memory_agent = MemoryAgent(
                    config=config_loader.get_agent_config("memory"),
                    memory_manager=memory_manager,
                )
                logger.info("MemoryAgent initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize MemoryAgent: {e}", exc_info=True)
                self.status_message = f"Error initializing MemoryAgent: {str(e)}"
                return False
                
        return True

# Create application state
app_state = AppState()

# --- Workflow Functions ---
async def search_and_memorize_workflow(query: str):
    """Execute a workflow to search the web and store results in memory."""
    if not app_state.initialize_agents():
        app_state.status_message = "Failed to initialize agents. Please check logs."
        return
    
    app_state.is_processing = True
    app_state.status_message = f"Searching for '{query}'..."
    mp.update()
    
    try:
        # Step 1: Search the web
        search_task = Task(
            description=f"Search web for '{query}'",
            agent_id="web_surfer",
            inputs={"query": query},
        )
        
        search_result = await app_state.web_surfer_agent.execute(search_task)
        
        if search_result.get("status") != "completed":
            app_state.status_message = f"Search failed: {search_result.get('error', 'Unknown error')}"
            app_state.is_processing = False
            mp.update()
            return
        
        search_data = search_result.get("results", [])
        app_state.search_results = search_data
        
        # Format search results for storage
        content_to_store = []
        for item in search_data:
            if isinstance(item, dict):
                content_to_store.append({
                    "title": item.get("title", "No title"),
                    "snippet": item.get("snippet", "No snippet"),
                    "url": item.get("url", "No URL"),
                })
            else:
                content_to_store.append(str(item))
        
        # Step 2: Store in memory
        app_state.status_message = "Storing search results in memory..."
        mp.update()
        
        memory_task = Task(
            description="Store search findings in memory",
            agent_id="memory",
            inputs={
                "content_to_store": content_to_store,
                "memory_topic": query,
                "memory_type": "FACT",
                "tags": ["web_search", query],
            },
        )
        
        memory_result = await app_state.memory_agent.execute(memory_task)
        
        if memory_result.get("status") != "completed":
            app_state.status_message = f"Memory storage failed: {memory_result.get('error', 'Unknown error')}"
            app_state.is_processing = False
            mp.update()
            return
        
        app_state.status_message = f"Successfully searched for '{query}' and stored results in memory."
    except Exception as e:
        logger.error(f"Error in search and memorize workflow: {e}", exc_info=True)
        app_state.status_message = f"Error: {str(e)}"
    finally:
        app_state.is_processing = False
        mp.update()

async def recall_from_memory_workflow(query: str):
    """Execute a workflow to recall information from memory."""
    if not app_state.initialize_agents():
        app_state.status_message = "Failed to initialize agents. Please check logs."
        return
    
    app_state.is_processing = True
    app_state.status_message = f"Searching memory for '{query}'..."
    mp.update()
    
    try:
        memory_task = Task(
            description=f"Search memory for '{query}'",
            agent_id="memory",
            inputs={
                "query": query,
                "max_results": 5,
            },
        )
        
        memory_result = await app_state.memory_agent.execute(memory_task)
        
        if memory_result.get("status") != "completed":
            app_state.status_message = f"Memory search failed: {memory_result.get('error', 'Unknown error')}"
            app_state.is_processing = False
            mp.update()
            return
        
        retrieved_content = memory_result.get("retrieved_content", [])
        app_state.memory_results = retrieved_content
        
        if not retrieved_content:
            app_state.status_message = f"No memories found for '{query}'."
        else:
            app_state.status_message = f"Found {len(retrieved_content)} memories for '{query}'."
    except Exception as e:
        logger.error(f"Error in recall from memory workflow: {e}", exc_info=True)
        app_state.status_message = f"Error: {str(e)}"
    finally:
        app_state.is_processing = False
        mp.update()

# --- Mesop UI Handlers ---
@mp.page(path="/")
def memory_system_page():
    """Main memory system interface page."""
    mp.title("Agentic Kernel Memory System")
    
    # Initialize agents on first load
    if app_state.web_surfer_agent is None or app_state.memory_agent is None:
        app_state.initialize_agents()
    
    # Main container
    with container(style={"padding": "20px", "maxWidth": "800px", "margin": "0 auto"}):
        # Header
        with container(style={"marginBottom": "20px"}):
            markdown("# Agentic Kernel Memory System")
            markdown("This demo showcases how agents can store and retrieve information across interactions.")
        
        # Tabs for different operations
        with tabs():
            # Search and Memorize tab
            with tab("Search & Memorize"):
                with container(style={"padding": "10px"}):
                    markdown("## Search Web & Store in Memory")
                    markdown("Enter a topic to search for and store the results in memory.")
                    
                    # Search input
                    with container(style={"display": "flex", "gap": "10px", "marginBottom": "20px"}):
                        search_input = text_input(
                            placeholder="Enter search topic...",
                            disabled=app_state.is_processing,
                            style={"flexGrow": 1},
                        )
                        
                        def on_search():
                            query = search_input.value
                            if query:
                                app_state.search_query = query
                                search_input.value = ""
                                mp.update()
                                mp.spawn(search_and_memorize_workflow(query))
                        
                        button(
                            "Search & Store",
                            on_click=on_search,
                            disabled=app_state.is_processing,
                            style={"padding": "10px 20px"},
                        )
                    
                    # Search results
                    if app_state.search_results:
                        markdown("### Search Results")
                        with container(style={"border": "1px solid #ddd", "padding": "10px", "marginBottom": "20px", "maxHeight": "300px", "overflowY": "auto"}):
                            for i, result in enumerate(app_state.search_results):
                                with container(style={"marginBottom": "10px", "padding": "10px", "border": "1px solid #eee"}):
                                    if isinstance(result, dict):
                                        markdown(f"**{result.get('title', 'No title')}**")
                                        markdown(f"{result.get('snippet', 'No snippet')}")
                                        markdown(f"[{result.get('url', 'No URL')}]({result.get('url', '#')})")
                                    else:
                                        markdown(f"{result}")
            
            # Recall from Memory tab
            with tab("Recall from Memory"):
                with container(style={"padding": "10px"}):
                    markdown("## Recall from Memory")
                    markdown("Enter a topic to retrieve related information from memory.")
                    
                    # Memory search input
                    with container(style={"display": "flex", "gap": "10px", "marginBottom": "20px"}):
                        memory_input = text_input(
                            placeholder="Enter memory search topic...",
                            disabled=app_state.is_processing,
                            style={"flexGrow": 1},
                        )
                        
                        def on_memory_search():
                            query = memory_input.value
                            if query:
                                app_state.memory_query = query
                                memory_input.value = ""
                                mp.update()
                                mp.spawn(recall_from_memory_workflow(query))
                        
                        button(
                            "Search Memory",
                            on_click=on_memory_search,
                            disabled=app_state.is_processing,
                            style={"padding": "10px 20px"},
                        )
                    
                    # Memory results
                    if app_state.memory_results:
                        markdown("### Memory Results")
                        with container(style={"border": "1px solid #ddd", "padding": "10px", "marginBottom": "20px", "maxHeight": "300px", "overflowY": "auto"}):
                            for i, memory in enumerate(app_state.memory_results):
                                with container(style={"marginBottom": "10px", "padding": "10px", "border": "1px solid #eee"}):
                                    content = memory.get("content", "No content")
                                    metadata = memory.get("metadata", {})
                                    
                                    # Display memory content
                                    if isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, dict):
                                                markdown(f"**{item.get('title', 'No title')}**")
                                                markdown(f"{item.get('snippet', 'No snippet')}")
                                                markdown(f"[{item.get('url', 'No URL')}]({item.get('url', '#')})")
                                            else:
                                                markdown(f"{item}")
                                    else:
                                        markdown(f"{content}")
                                    
                                    # Display metadata
                                    if metadata:
                                        with container(style={"fontSize": "0.8em", "color": "#666", "marginTop": "5px"}):
                                            topic = metadata.get("topic", "")
                                            if topic:
                                                markdown(f"*Topic: {topic}*")
                                            
                                            tags = memory.get("tags", [])
                                            if tags:
                                                markdown(f"*Tags: {', '.join(tags)}*")
        
        # Status message
        if app_state.status_message:
            with container(style={"marginTop": "20px", "padding": "10px", "backgroundColor": "#f0f0f0", "borderRadius": "5px"}):
                markdown(f"**Status:** {app_state.status_message}")
                
                if app_state.is_processing:
                    markdown("*Processing...*")

# --- Main Execution ---
if __name__ == "__main__":
    # Start Mesop server
    mp.run()