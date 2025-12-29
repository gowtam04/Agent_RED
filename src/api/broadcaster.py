"""Event broadcasting system for real-time dashboard updates."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


@dataclass
class AgentThought:
    """Represents an agent's reasoning/thought process."""

    timestamp: datetime
    agent_type: str  # ORCHESTRATOR, NAVIGATION, BATTLE, MENU
    reasoning: str
    action: str
    result_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_type": self.agent_type,
            "reasoning": self.reasoning,
            "action": self.action,
            "result_data": self.result_data,
        }


@dataclass
class GameEvent:
    """Represents a game event (battle start, level up, map change, etc.)."""

    timestamp: datetime
    event_type: str  # map_change, battle_start, battle_end, level_up, item_obtained, etc.
    description: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "description": self.description,
            "data": self.data,
        }


# Type alias for async callback
AsyncCallback = Callable[[str, Any], Coroutine[Any, Any, None]]


class EventBroadcaster:
    """Manages event broadcasting to WebSocket clients.

    Maintains a history of recent thoughts and events for new clients,
    and notifies all registered listeners when new events occur.
    """

    def __init__(self, max_thoughts: int = 50, max_events: int = 100):
        """Initialize the broadcaster.

        Args:
            max_thoughts: Maximum number of agent thoughts to keep in history.
            max_events: Maximum number of game events to keep in history.
        """
        self.thoughts: deque[AgentThought] = deque(maxlen=max_thoughts)
        self.events: deque[GameEvent] = deque(maxlen=max_events)
        self._listeners: list[AsyncCallback] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async notifications."""
        self._loop = loop

    def add_listener(self, callback: AsyncCallback) -> None:
        """Register a callback for all messages.

        Args:
            callback: Async function(msg_type, data) to call on events.
        """
        self._listeners.append(callback)

    def remove_listener(self, callback: AsyncCallback) -> None:
        """Remove a registered callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def add_thought(self, thought: AgentThought) -> None:
        """Add an agent thought and notify listeners.

        Args:
            thought: The agent's thought/reasoning to broadcast.
        """
        self.thoughts.append(thought)
        self._notify("AGENT_THOUGHT", thought.to_dict())
        logger.debug(
            "Agent thought broadcast",
            agent=thought.agent_type,
            action=thought.action,
        )

    def add_event(self, event: GameEvent) -> None:
        """Add a game event and notify listeners.

        Args:
            event: The game event to broadcast.
        """
        self.events.append(event)
        self._notify("EVENT", event.to_dict())
        logger.debug(
            "Game event broadcast",
            event_type=event.event_type,
            description=event.description,
        )

    def get_recent_thoughts(self, count: int = 20) -> list[dict[str, Any]]:
        """Get the most recent agent thoughts.

        Args:
            count: Maximum number of thoughts to return.

        Returns:
            List of thought dictionaries.
        """
        thoughts = list(self.thoughts)[-count:]
        return [t.to_dict() for t in thoughts]

    def get_recent_events(self, count: int = 50) -> list[dict[str, Any]]:
        """Get the most recent game events.

        Args:
            count: Maximum number of events to return.

        Returns:
            List of event dictionaries.
        """
        events = list(self.events)[-count:]
        return [e.to_dict() for e in events]

    def _notify(self, msg_type: str, data: Any) -> None:
        """Notify all listeners of a new message.

        Args:
            msg_type: The type of message (AGENT_THOUGHT, EVENT).
            data: The message data.
        """
        if not self._listeners:
            return

        loop = self._loop
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop - skip async notification
                logger.debug("No event loop available for notification")
                return

        for callback in self._listeners:
            try:
                asyncio.run_coroutine_threadsafe(callback(msg_type, data), loop)
            except Exception as e:
                logger.warning("Failed to notify listener", error=str(e))


# Global broadcaster instance
_broadcaster: EventBroadcaster | None = None


def get_broadcaster() -> EventBroadcaster:
    """Get the global event broadcaster instance."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster
