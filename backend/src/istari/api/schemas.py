"""Pydantic schemas for API request/response validation."""

import datetime

from pydantic import BaseModel, ConfigDict

# --- TODO schemas ---


class TodoCreate(BaseModel):
    title: str


class TodoUpdate(BaseModel):
    title: str | None = None
    body: str | None = None
    priority: int | None = None
    due_date: datetime.datetime | None = None
    tags: list[str] | None = None
    status: str | None = None


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str | None = None
    status: str
    priority: int | None = None
    urgent: bool | None = None
    important: bool | None = None
    source: str | None = None
    source_link: str | None = None
    due_date: datetime.datetime | None = None
    tags: list[str] | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class TodoListResponse(BaseModel):
    todos: list[TodoResponse]


class PrioritizedTodosResponse(BaseModel):
    todos: list[TodoResponse]
    reasoning: str | None = None


# --- Memory schemas ---


class MemoryCreate(BaseModel):
    content: str


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    content: str
    confidence: float
    source: str | None = None
    created_at: datetime.datetime


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]


# --- Settings schemas ---


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str


class SettingsResponse(BaseModel):
    settings: dict[str, str]


# --- Notification schemas ---


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    content: str
    read: bool
    read_at: datetime.datetime | None = None
    suppressed_by: str | None = None
    completed: bool = False
    completed_at: datetime.datetime | None = None
    created_at: datetime.datetime


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class UnreadCountResponse(BaseModel):
    count: int


# --- Digest schemas ---


class DigestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    content_summary: str
    items_json: dict[str, object] | None = None
    reviewed: bool
    reviewed_at: datetime.datetime | None = None
    created_at: datetime.datetime


class DigestListResponse(BaseModel):
    digests: list[DigestResponse]


# --- Chat schemas ---


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime.datetime
    todo_created: bool = False
    todo_updated: bool = False
    memory_created: bool = False
