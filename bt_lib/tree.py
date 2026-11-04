"""
Behavior Tree - Main tree container and execution logic.
"""

from typing import Any

from .blackboard import Blackboard
from .nodes import Action, Condition, Node, NodeStatus


class BehaviorTree:
    """
    Behavior Tree container.
    Holds root node, blackboard, and execution state.
    """

    def __init__(self, root: Node, name: str = "BehaviorTree"):
        self.root = root
        self.name = name
        self.blackboard = Blackboard()
        self._tick_count = 0
        self._last_status: NodeStatus | None = None
        self._history: list[dict[str, Any]] = []

        root.blackboard = self.blackboard

    def tick(self, max_ticks: int = 1000) -> NodeStatus:
        """
        Run tree until completion or max_ticks.
        Returns final status.
        """
        self._tick_count = 0
        self._history = []

        while self._tick_count < max_ticks:
            self._tick_count += 1
            status = self.root.tick(self.blackboard)
            self._last_status = status

            self._history.append({
                "tick": self._tick_count,
                "status": status.value,
                "blackboard": self.blackboard.to_dict()
            })

            if status != NodeStatus.RUNNING:
                break

        return status

    def tick_once(self) -> NodeStatus:
        """Execute exactly one tick."""
        self._tick_count += 1
        status = self.root.tick(self.blackboard)
        self._last_status = status

        self._history.append({
            "tick": self._tick_count,
            "status": status.value,
            "blackboard": self.blackboard.to_dict()
        })

        return status

    def reset(self) -> None:
        """Reset tree for re-execution."""
        self.root.reset()
        self.blackboard = Blackboard()
        self.root.blackboard = self.blackboard
        self._tick_count = 0
        self._last_status = None
        self._history = []

    def get_status(self) -> NodeStatus | None:
        return self._last_status

    def get_history(self) -> list[dict[str, Any]]:
        return self._history

    def set_blackboard(self, key: str, value: Any) -> None:
        self.blackboard.set(key, value)

    def get_blackboard(self, key: str, default: Any = None) -> Any:
        return self.blackboard.get(key, default)

    def __repr__(self) -> str:
        return f"BehaviorTree({self.name}, root={self.root})"


def build_tree_from_dict(data: dict[str, Any]) -> Node:
    """Build a tree from a dictionary (parsed from XML/JSON/YAML)."""
    from .nodes import Inverter, Parallel, Repeater, Selector, Sequence, Timeout, UntilSuccess

    NODE_TYPES = {
        "Sequence": Sequence,
        "Selector": Selector,
        "Parallel": Parallel,
        "Action": Action,
        "Condition": Condition,
        "Inverter": Inverter,
        "Repeater": Repeater,
        "UntilSuccess": UntilSuccess,
        "Timeout": Timeout,
    }

    def build_node(node_data: dict[str, Any]) -> Node:
        node_type = node_data.get("type", "Sequence")
        name = node_data.get("name", node_type)
        properties = node_data.get("properties", {})
        children_data = node_data.get("children", [])

        cls = NODE_TYPES.get(node_type, Sequence)
        node = cls(name=name, **properties)

        for child_data in children_data:
            child = build_node(child_data)
            node.add_child(child)

        return node

    return build_node(data)


def run_tree(tree: BehaviorTree, max_ticks: int = 1000) -> NodeStatus:
    """Convenience function to run a tree to completion."""
    return tree.tick(max_ticks)
