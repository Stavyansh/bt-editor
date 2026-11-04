"""
Blackboard - Shared state storage for behavior tree nodes.
Allows nodes to communicate via key-value pairs.
"""

from typing import Any, Optional


class Blackboard:
    """
    Hierarchical blackboard with parent-child scoping.
    Child blackboards can read from parent, but writes are local.
    """

    def __init__(self, parent: Optional["Blackboard"] = None, data: dict[str, Any] | None = None):
        self._data: dict[str, Any] = data or {}
        self._parent = parent

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from this blackboard or parent."""
        if key in self._data:
            return self._data[key]
        if self._parent:
            return self._parent.get(key, default)
        return default

    def set(self, key: str, value: Any) -> None:
        """Set value in this blackboard (not parent)."""
        self._data[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists in this blackboard or parent."""
        if key in self._data:
            return True
        if self._parent:
            return self._parent.has(key)
        return False

    def delete(self, key: str) -> bool:
        """Delete key from this blackboard. Returns True if deleted."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def child(self) -> "Blackboard":
        """Create a child blackboard with this as parent."""
        return Blackboard(parent=self)

    def merge(self, other: "Blackboard") -> None:
        """Merge another blackboard's data into this one (shallow)."""
        self._data.update(other._data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict (including parent chain)."""
        result = {}
        if self._parent:
            result.update(self._parent.to_dict())
        result.update(self._data)
        return result

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __getitem__(self, key: str) -> Any:
        value = self.get(key)
        if value is None and key not in self:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __repr__(self) -> str:
        return f"Blackboard({self.to_dict()})"
