from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, validator


class SkillDefinition(BaseModel):
    """Definition of a skill that an agent possesses."""
    name: str = Field(..., description="Name of the skill")
    description: str | None = Field(None, description="Description of the skill")
    parameters: dict[str, Any] | None = Field(
        None, description="Parameters required by the skill",
    )


class AgentCard(BaseModel):
    """Core information about an agent for discovery."""
    agent_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the agent")
    name: str = Field(..., description="Name of the agent")
    description: str | None = Field(None, description="Description of the agent")
    endpoint: HttpUrl = Field(..., description="Endpoint URL for the agent's API")
    skills: list[SkillDefinition] | None = Field(
        None, description="List of skills the agent possesses",
    )
    protocol_version: str = Field("1.0", description="Version of the A2A protocol supported")
    authentication: dict[str, Any] | None = Field(
        None, description="Authentication details required by the agent",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the agent card was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the agent card was last updated",
    )

    @validator("updated_at", always=True)
    def set_updated_at(cls, _v, _values):
        """Ensures updated_at is always current."""
        return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    """Enumeration for task statuses."""
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TextPart(BaseModel):
    """Text content part for messages."""

    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")
    mime_type: str = Field("text/plain", description="MIME type of the text")


class FilePart(BaseModel):
    """File content part for messages."""

    type: Literal["file"] = "file"
    file_id: str = Field(..., description="Identifier for the file")
    file_name: str = Field(..., description="Name of the file")
    mime_type: str = Field(..., description="MIME type of the file")
    url: HttpUrl | None = Field(None, description="URL to access the file")


class DataPart(BaseModel):
    """Structured data content part for messages."""

    type: Literal["data"] = "data"
    data: dict[str, Any] = Field(..., description="Structured data content")
    mime_type: str = Field("application/json", description="MIME type of the data")


Part = TextPart | FilePart | DataPart


class Message(BaseModel):
    """Represents a message within a task conversation."""
    message_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the message")
    role: str = Field(..., description="Role of the message sender (e.g., 'user', 'agent')")
    parts: list[Part] = Field(..., description="List of content parts constituting the message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the message was created",
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Optional metadata associated with the message",
    )


class Task(BaseModel):
    """Represents a task assigned to an agent."""
    task_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the task")
    title: str = Field(..., description="Title or brief description of the task")
    description: str | None = Field(None, description="Detailed description of the task")
    messages: list[Message] = Field(
        default_factory=list, description="Conversation history related to the task",
    )
    status: TaskStatus = Field(
        TaskStatus.SUBMITTED, description="Current status of the task",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the task was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the task was last updated",
    )
    expires_at: datetime | None = Field(None, description="Optional expiration timestamp for the task")
    result: Any | None = Field(None, description="Result of the task upon completion")
    metadata: dict[str, Any] | None = Field(
        None, description="Optional metadata associated with the task",
    )

    @validator("updated_at", always=True)
    def set_updated_at(cls, _v, _values):
        """Ensures updated_at is always current."""
        return datetime.now(timezone.utc)


class TaskInput(BaseModel):
    """Input structure for creating a new task."""
    title: str = Field(..., description="Title of the task")
    description: str | None = Field(None, description="Description of the task")
    message: Message | None = Field(None, description="Initial message to start the task")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for the task")


class TaskUpdate(BaseModel):
    """Input structure for updating a task (e.g., adding a message)."""
    message: Message = Field(..., description="New message to add to the task conversation")


class TaskOutput(BaseModel):
    """Output structure representing the state or result of a task."""
    task_id: UUID = Field(..., description="Identifier of the task")
    status: TaskStatus = Field(..., description="Current status of the task")
    messages: list[Message] | None = Field(
        None, description="Updated conversation history",
    )
    result: Any | None = Field(None, description="Result of the task, if completed")
    error: str | None = Field(None, description="Error message, if the task failed")


class SubscribeInput(BaseModel):
    """Input structure for subscribing to task updates."""
    task_id: UUID = Field(..., description="Identifier of the task to subscribe to")
    callback_url: HttpUrl = Field(..., description="URL to receive updates")


class PushNotificationConfig(BaseModel):
    """Configuration for push notifications."""
    endpoint: HttpUrl = Field(..., description="The endpoint URL for the push notification service.")
    event_types: list[str] | None = Field(
        None,
        description="Specific event types to subscribe to (e.g., 'task_updated', 'message_added'). If None, subscribe to all relevant events.",
    )


class SetPushNotificationInput(BaseModel):
    """Input structure for setting up push notifications for a task."""

    task_id: UUID = Field(..., description="ID of the task to receive notifications for")
    config: PushNotificationConfig = Field(..., description="Push notification configuration")


class GetPushNotificationOutput(BaseModel):
    """Output structure for retrieving push notification configuration."""

    id: UUID = Field(default_factory=uuid4, description="ID of the push notification config")
    config: PushNotificationConfig = Field(..., description="Push notification configuration")
