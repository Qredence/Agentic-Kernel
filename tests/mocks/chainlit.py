"""Mock classes for Chainlit components.

These mock classes allow testing integrations with Chainlit
without requiring an actual Chainlit installation or server.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union

class TaskStatus(Enum):
    """Mock for Chainlit TaskStatus enum."""
    READY = "ready"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

class Task:
    """Mock for Chainlit Task class."""
    
    def __init__(self, title: str, status: Optional[Union[TaskStatus, str]] = None):
        """Initialize a Task with title and status."""
        self.title = title
        self.status = status
        self.forId = None

class TaskList:
    """Mock for Chainlit TaskList class."""
    
    def __init__(self):
        """Initialize a TaskList."""
        self.tasks: List[Task] = []
        self.status = "Ready"
    
    async def add_task(self, task: Task):
        """Add a task to the TaskList."""
        self.tasks.append(task)
        return task
    
    async def send(self):
        """Send the TaskList to the UI (mocked)."""
        # In a real implementation, this would update the UI
        pass

class Message:
    """Mock for Chainlit Message class."""
    
    def __init__(self, content: str = "", author: Optional[str] = None):
        """Initialize a Message with content and author."""
        self.content = content
        self.author = author
        self.id = f"msg_{id(self)}"  # Generate a unique ID for the message
        self._tokens = []
        
    async def send(self):
        """Send the message (mocked)."""
        # In a real implementation, this would send the message to the UI
        return self
        
    async def stream_token(self, token: str):
        """Stream a token to the message (mocked)."""
        self._tokens.append(token)
        self.content += token
        
    async def update(self):
        """Update the message (mocked)."""
        # In a real implementation, this would update the message in the UI
        pass

class Step:
    """Mock for Chainlit Step class."""
    
    def __init__(self, name: str = "", type: str = ""):
        """Initialize a Step with name and type."""
        self.name = name
        self.type = type
        self.input = None
        self.output = None
        
    async def __aenter__(self):
        """Enter the step context."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the step context."""
        pass
        
    async def stream_token(self, token: str):
        """Stream a token to the step (mocked)."""
        pass

class UserSession:
    """Mock for Chainlit user_session."""
    
    def __init__(self):
        """Initialize a UserSession."""
        self._data: Dict[str, Any] = {}
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the session."""
        return self._data.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a value in the session."""
        self._data[key] = value

# Singleton user session instance
user_session = UserSession()

def on_chat_start(func):
    """Mock for cl.on_chat_start decorator."""
    return func

def on_message(func):
    """Mock for cl.on_message decorator."""
    return func

def set_chat_profiles(func):
    """Mock for cl.set_chat_profiles decorator."""
    return func 