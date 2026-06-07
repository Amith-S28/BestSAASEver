"""Conversation storage — JSON-file-based chat history per folder.

Conversations are stored as individual JSON files:
  data/conversations/{folder_id}/{conv_id}.json

This keeps chat history simple, portable, and easy to browse.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path

from medrag.config import settings


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    sources: list[str] = field(default_factory=list)


@dataclass
class Conversation:
    """A full conversation thread."""

    conv_id: str
    folder_id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "conv_id": self.conv_id,
            "folder_id": self.folder_id,
            "title": self.title,
            "messages": [
                {"role": m.role, "content": m.content, "sources": m.sources}
                for m in self.messages
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Conversation:
        return cls(
            conv_id=data["conv_id"],
            folder_id=data["folder_id"],
            title=data["title"],
            messages=[
                ChatMessage(
                    role=m["role"],
                    content=m["content"],
                    sources=m.get("sources", []),
                )
                for m in data.get("messages", [])
            ],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


class ConversationDatabase:
    """Manage conversation history stored as JSON files."""

    def __init__(self, conversations_dir: str | None = None):
        self.base_dir = Path(conversations_dir or settings.data_dir) / "conversations"

    def _folder_dir(self, folder_id: str) -> Path:
        d = self.base_dir / folder_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _conv_path(self, folder_id: str, conv_id: str) -> Path:
        return self._folder_dir(folder_id) / f"{conv_id}.json"

    def create_conversation(self, folder_id: str, title: str = "New conversation") -> Conversation:
        """Start a new conversation in a folder."""
        conv_id = f"conv_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()

        conv = Conversation(
            conv_id=conv_id,
            folder_id=folder_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

        path = self._conv_path(folder_id, conv_id)
        path.write_text(json.dumps(conv.to_dict(), indent=2), encoding="utf-8")
        return conv

    def add_message(self, folder_id: str, conv_id: str, message: ChatMessage) -> Conversation | None:
        """Append a message to an existing conversation."""
        conv = self.load_conversation(folder_id, conv_id)
        if conv is None:
            return None

        conv.messages.append(message)
        conv.updated_at = datetime.now(timezone.utc).isoformat()

        # Auto-title from first user message
        if conv.title == "New conversation" and message.role == "user":
            conv.title = message.content[:60] + ("..." if len(message.content) > 60 else "")

        path = self._conv_path(folder_id, conv_id)
        path.write_text(json.dumps(conv.to_dict(), indent=2), encoding="utf-8")
        return conv

    def load_conversation(self, folder_id: str, conv_id: str) -> Conversation | None:
        """Load a full conversation by ID."""
        path = self._conv_path(folder_id, conv_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Conversation.from_dict(data)

    def list_conversations(self, folder_id: str) -> list[dict]:
        """List conversation summaries for a folder (newest first)."""
        folder_dir = self._folder_dir(folder_id)
        convs = []
        for path in sorted(folder_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                convs.append({
                    "conv_id": data["conv_id"],
                    "folder_id": data["folder_id"],
                    "title": data["title"],
                    "message_count": len(data.get("messages", [])),
                    "created_at": data.get("created_at", ""),
                    "updated_at": data.get("updated_at", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return convs

    def delete_conversation(self, folder_id: str, conv_id: str) -> bool:
        """Delete a conversation file."""
        path = self._conv_path(folder_id, conv_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def delete_folder_conversations(self, folder_id: str) -> int:
        """Delete all conversations for a folder. Returns count deleted."""
        folder_dir = self._folder_dir(folder_id)
        count = 0
        for path in folder_dir.glob("*.json"):
            path.unlink()
            count += 1
        return count