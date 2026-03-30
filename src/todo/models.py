"""Pydantic models for Todo and Config."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import IntEnum, StrEnum

from pydantic import BaseModel, Field, field_validator


class Priority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    NONE = 5

    @property
    def label(self) -> str:
        return {1: "Critical", 2: "High", 3: "Medium", 4: "Low", 5: "None"}[self.value]

    @property
    def color(self) -> str:
        return {
            1: "red",
            2: "orange3",
            3: "yellow",
            4: "dodger_blue2",
            5: "dim",
        }[self.value]


class Status(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


def _generate_id() -> str:
    return uuid.uuid4().hex[:6]


class Todo(BaseModel):
    id: str = Field(default_factory=_generate_id)
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    category: str
    project: str | None = None
    status: Status = Status.TODO
    tags: list[str] = Field(default_factory=list)
    due_date: str | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be empty")
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def coerce_priority(cls, v: int | Priority) -> Priority:
        return Priority(v)


class ConfigDefaults(BaseModel):
    category: str = "Work"
    priority: Priority = Priority.MEDIUM
    projects_roots: list[str] = Field(default_factory=lambda: ["~/projects", "~/work"])


class TodoConfig(BaseModel):
    categories: list[str] = Field(
        default_factory=lambda: [
            "Work",
            "Family",
            "Hobbies",
            "Health",
            "Finance",
            "Education",
            "Social",
        ]
    )
    defaults: ConfigDefaults = Field(default_factory=ConfigDefaults)
