"""Long-term memory with persistent JSON storage for Manus Agent Core."""

import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from exceptions import MemoryError


@dataclass
class LongTermMemoryEntry:
    """Persistent memory entry."""
    
    key: str
    value: Any
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "key": self.key,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
    
    @staticmethod
    def from_dict(data: dict) -> "LongTermMemoryEntry":
        """Create from dict."""
        return LongTermMemoryEntry(
            key=data["key"],
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


class LongTermMemory:
    """Persistent long-term memory with JSON file storage.
    
    Stores key-value pairs persistently across agent sessions.
    Useful for remembering facts, preferences, and learned information.
    """
    
    def __init__(self, storage_path: str | Path = "./data/memory.json", auto_save: bool = True):
        """Initialize long-term memory.
        
        Args:
            storage_path: Path to JSON storage file
            auto_save: Automatically save to disk after each update
        """
        self.storage_path = Path(storage_path)
        self.auto_save = auto_save
        self._memory: dict[str, LongTermMemoryEntry] = {}
        
        # Create storage directory if needed
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing memory
        self.load()
    
    def set(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> None:
        """Store a key-value pair in memory.
        
        Args:
            key: Memory key
            value: Value to store (must be JSON-serializable)
            metadata: Optional metadata dict
        """
        entry = LongTermMemoryEntry(
            key=key,
            value=value,
            metadata=metadata or {}
        )
        self._memory[key] = entry
        
        if self.auto_save:
            self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from memory.
        
        Args:
            key: Memory key
            default: Default value if key not found
        
        Returns:
            Stored value or default
        """
        entry = self._memory.get(key)
        return entry.value if entry else default
    
    def get_entry(self, key: str) -> LongTermMemoryEntry | None:
        """Get full memory entry with metadata.
        
        Args:
            key: Memory key
        
        Returns:
            Memory entry or None
        """
        return self._memory.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete a key from memory.
        
        Args:
            key: Memory key
        
        Returns:
            True if key was deleted, False if not found
        """
        if key in self._memory:
            del self._memory[key]
            if self.auto_save:
                self.save()
            return True
        return False
    
    def has(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self._memory
    
    def keys(self) -> list[str]:
        """Get all memory keys."""
        return list(self._memory.keys())
    
    def all(self) -> dict[str, Any]:
        """Get all stored key-value pairs."""
        return {key: entry.value for key, entry in self._memory.items()}
    
    def clear(self) -> None:
        """Clear all memory."""
        self._memory.clear()
        if self.auto_save:
            self.save()
    
    def save(self) -> None:
        """Save memory to disk."""
        try:
            data = {
                key: entry.to_dict()
                for key, entry in self._memory.items()
            }
            
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            raise MemoryError(f"Failed to save memory: {e}")
    
    def load(self) -> None:
        """Load memory from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            self._memory = {
                key: LongTermMemoryEntry.from_dict(entry_data)
                for key, entry_data in data.items()
            }
        except Exception as e:
            raise MemoryError(f"Failed to load memory: {e}")
    
    def count(self) -> int:
        """Get number of stored items."""
        return len(self._memory)
