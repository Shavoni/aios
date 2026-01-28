"""Session and conversation management for multi-turn interactions."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in a conversation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    agent_id: str | None = None
    agent_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A conversation session with message history."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "anonymous"
    department: str = "General"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    messages: list[Message] = Field(default_factory=list)
    current_agent_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)  # Persistent context
    is_active: bool = True
    title: str | None = None  # Auto-generated from first message


class UserPreferences(BaseModel):
    """User preferences and learned context."""

    user_id: str
    department: str = "General"
    preferred_language: str = "en"
    preferred_response_style: str = "professional"  # professional, casual, concise
    frequently_used_agents: list[str] = Field(default_factory=list)
    custom_settings: dict[str, Any] = Field(default_factory=dict)
    last_active: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SessionManager:
    """Manages conversation sessions and user context."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "data", "sessions"
            )
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Conversations storage
        self._conversations_path = self.storage_path / "conversations"
        self._conversations_path.mkdir(exist_ok=True)

        # User preferences storage
        self._prefs_path = self.storage_path / "preferences.json"
        self._preferences: dict[str, UserPreferences] = {}
        self._load_preferences()

        # Active sessions cache (in-memory for performance)
        self._active_sessions: dict[str, Conversation] = {}

    def _load_preferences(self) -> None:
        """Load user preferences from storage."""
        if self._prefs_path.exists():
            try:
                with open(self._prefs_path) as f:
                    data = json.load(f)
                    for user_id, prefs in data.items():
                        self._preferences[user_id] = UserPreferences(**prefs)
            except Exception:
                self._preferences = {}

    def _save_preferences(self) -> None:
        """Save user preferences to storage."""
        data = {k: v.model_dump() for k, v in self._preferences.items()}
        with open(self._prefs_path, "w") as f:
            json.dump(data, f, indent=2)

    def _conversation_file(self, conv_id: str) -> Path:
        """Get the file path for a conversation."""
        return self._conversations_path / f"{conv_id}.json"

    def _load_conversation(self, conv_id: str) -> Conversation | None:
        """Load a conversation from storage."""
        file_path = self._conversation_file(conv_id)
        if file_path.exists():
            try:
                with open(file_path) as f:
                    return Conversation(**json.load(f))
            except Exception:
                return None
        return None

    def _save_conversation(self, conv: Conversation) -> None:
        """Save a conversation to storage."""
        file_path = self._conversation_file(conv.id)
        with open(file_path, "w") as f:
            json.dump(conv.model_dump(), f, indent=2)

    # =========================================================================
    # Conversation Management
    # =========================================================================

    def create_conversation(
        self,
        user_id: str = "anonymous",
        department: str = "General",
    ) -> Conversation:
        """Create a new conversation session."""
        conv = Conversation(user_id=user_id, department=department)
        self._active_sessions[conv.id] = conv
        self._save_conversation(conv)
        return conv

    def get_conversation(self, conv_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        # Check cache first
        if conv_id in self._active_sessions:
            return self._active_sessions[conv_id]
        # Load from storage
        conv = self._load_conversation(conv_id)
        if conv:
            self._active_sessions[conv_id] = conv
        return conv

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        agent_id: str | None = None,
        agent_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message | None:
        """Add a message to a conversation."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return None

        message = Message(
            role=role,
            content=content,
            agent_id=agent_id,
            agent_name=agent_name,
            metadata=metadata or {},
        )
        conv.messages.append(message)
        conv.updated_at = datetime.utcnow().isoformat()

        # Set title from first user message
        if not conv.title and role == "user":
            conv.title = content[:50] + ("..." if len(content) > 50 else "")

        # Update current agent
        if agent_id:
            conv.current_agent_id = agent_id

        self._save_conversation(conv)
        return message

    def get_conversation_context(
        self,
        conv_id: str,
        max_messages: int = 10,
        max_tokens: int = 4000,
    ) -> str:
        """Get conversation context for LLM prompt."""
        conv = self.get_conversation(conv_id)
        if not conv or not conv.messages:
            return ""

        # Get recent messages (respecting limits)
        recent = conv.messages[-max_messages:]

        context_parts = []
        total_chars = 0
        char_limit = max_tokens * 4  # Rough token estimation

        for msg in reversed(recent):
            part = f"{msg.role.upper()}: {msg.content}"
            if total_chars + len(part) > char_limit:
                break
            context_parts.insert(0, part)
            total_chars += len(part)

        return "\n\n".join(context_parts)

    def list_conversations(
        self,
        user_id: str | None = None,
        limit: int = 50,
        include_inactive: bool = False,
    ) -> list[Conversation]:
        """List conversations, optionally filtered by user."""
        conversations = []

        # Load all conversation files
        for file_path in self._conversations_path.glob("*.json"):
            try:
                with open(file_path) as f:
                    conv = Conversation(**json.load(f))
                    if user_id and conv.user_id != user_id:
                        continue
                    if not include_inactive and not conv.is_active:
                        continue
                    conversations.append(conv)
            except Exception:
                continue

        # Sort by updated_at descending
        conversations.sort(key=lambda c: c.updated_at, reverse=True)
        return conversations[:limit]

    def close_conversation(self, conv_id: str) -> bool:
        """Mark a conversation as inactive."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return False

        conv.is_active = False
        conv.updated_at = datetime.utcnow().isoformat()
        self._save_conversation(conv)

        # Remove from active cache
        if conv_id in self._active_sessions:
            del self._active_sessions[conv_id]

        return True

    def update_context(
        self,
        conv_id: str,
        context: dict[str, Any],
    ) -> bool:
        """Update persistent context for a conversation."""
        conv = self.get_conversation(conv_id)
        if not conv:
            return False

        conv.context.update(context)
        conv.updated_at = datetime.utcnow().isoformat()
        self._save_conversation(conv)
        return True

    # =========================================================================
    # User Preferences
    # =========================================================================

    def get_user_preferences(self, user_id: str) -> UserPreferences:
        """Get or create user preferences."""
        if user_id not in self._preferences:
            self._preferences[user_id] = UserPreferences(user_id=user_id)
            self._save_preferences()
        return self._preferences[user_id]

    def update_user_preferences(
        self,
        user_id: str,
        updates: dict[str, Any],
    ) -> UserPreferences:
        """Update user preferences."""
        prefs = self.get_user_preferences(user_id)

        for key, value in updates.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

        prefs.last_active = datetime.utcnow().isoformat()
        self._save_preferences()
        return prefs

    def record_agent_usage(self, user_id: str, agent_id: str) -> None:
        """Record that a user used an agent (for recommendations)."""
        prefs = self.get_user_preferences(user_id)

        # Move agent to front of frequently used list
        if agent_id in prefs.frequently_used_agents:
            prefs.frequently_used_agents.remove(agent_id)
        prefs.frequently_used_agents.insert(0, agent_id)

        # Keep only top 10
        prefs.frequently_used_agents = prefs.frequently_used_agents[:10]

        prefs.last_active = datetime.utcnow().isoformat()
        self._save_preferences()

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_old_conversations(self, days: int = 30) -> int:
        """Delete conversations older than specified days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        deleted = 0

        for file_path in self._conversations_path.glob("*.json"):
            try:
                with open(file_path) as f:
                    conv = Conversation(**json.load(f))
                    if conv.updated_at < cutoff and not conv.is_active:
                        file_path.unlink()
                        deleted += 1
            except Exception:
                continue

        return deleted


# Singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


__all__ = [
    "Message",
    "Conversation",
    "UserPreferences",
    "SessionManager",
    "get_session_manager",
]
