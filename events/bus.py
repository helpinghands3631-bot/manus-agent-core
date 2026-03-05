"""Event bus for pub/sub messaging in Manus Agent Core."""

from typing import Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents an event in the system."""
    
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"


class EventBus:
    """Pub/sub event bus for agent lifecycle events.
    
    Supports:
    - Subscribe to specific event types
    - Publish events to all subscribers
    - Wildcard subscriptions (*)
    - Async-safe (thread-safe not guaranteed)
    
    Common event types:
    - agent.start: Agent execution started
    - agent.step: Agent completed a reasoning step
    - agent.tool_call: Agent called a tool
    - agent.error: Agent encountered an error
    - agent.complete: Agent finished execution
    """
    
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_history: list[Event] = []
        self._max_history = 1000
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type.
        
        Args:
            event_type: Event type to subscribe to (e.g., 'agent.step')
                       Use '*' to subscribe to all events
            handler: Callback function that receives Event objects
        """
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to '{event_type}' events")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                logger.debug(f"Unsubscribed from '{event_type}' events")
            except ValueError:
                pass
    
    def publish(self, event_type: str, data: dict[str, Any] | None = None, source: str = "unknown") -> None:
        """Publish an event to all subscribers.
        
        Args:
            event_type: Type of event (e.g., 'agent.step')
            data: Event payload data
            source: Source component that published the event
        """
        event = Event(
            type=event_type,
            data=data or {},
            source=source
        )
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify type-specific subscribers
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for '{event_type}': {e}")
        
        # Notify wildcard subscribers
        for handler in self._subscribers.get("*", []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in wildcard event handler: {e}")
    
    def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        """Get event history, optionally filtered by type.
        
        Args:
            event_type: Filter by event type (None = all events)
            limit: Maximum number of events to return
        
        Returns:
            List of recent events, most recent first
        """
        history = self._event_history[::-1]  # Reverse for most recent first
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[:limit]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.debug("Event history cleared")
