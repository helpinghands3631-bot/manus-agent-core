"""Short-term memory with sliding window for Manus Agent Core."""

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque


@dataclass
class MemoryEntry:
    """Single memory entry."""
    
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class ShortTermMemory:
    """Sliding window short-term memory for agent conversations.
    
    Maintains recent conversation history with automatic pruning.
    Useful for keeping context within LLM token limits.
    """
    
    def __init__(self, window_size: int = 10):
        """Initialize short-term memory.
        
        Args:
            window_size: Maximum number of messages to retain
        """
        self.window_size = window_size
        self._messages: deque[MemoryEntry] = deque(maxlen=window_size)
    
    def add(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Add a message to memory.
        
        Args:
            role: Message role ('user', 'assistant', 'system', 'tool')
            content: Message content
            metadata: Optional metadata dict
        """
        entry = MemoryEntry(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._messages.append(entry)
    
    def get_messages(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get recent messages formatted for LLM.
        
        Args:
            limit: Maximum messages to return (None = all)
        
        Returns:
            List of message dicts with 'role' and 'content'
        """
        messages = list(self._messages)
        if limit:
            messages = messages[-limit:]
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"metadata": msg.metadata} if msg.metadata else {})
            }
            for msg in messages
        ]
    
    def get_entries(self) -> list[MemoryEntry]:
        """Get all memory entries with full metadata."""
        return list(self._messages)
    
    def clear(self) -> None:
        """Clear all messages from memory."""
        self._messages.clear()
    
    def get_context_string(self, separator: str = "\n\n") -> str:
        """Get memory as a formatted context string.
        
        Args:
            separator: String to join messages
        
        Returns:
            Formatted conversation history
        """
        return separator.join([
            f"{msg.role}: {msg.content}"
            for msg in self._messages
        ])
    
    def count(self) -> int:
        """Get current number of messages in memory."""
        return len(self._messages)
    
    def is_full(self) -> bool:
        """Check if memory window is at capacity."""
        return len(self._messages) == self.window_size
