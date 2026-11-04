"""
Behavior Tree Node Definitions

Node Status:
- SUCCESS: Node completed successfully
- FAILURE: Node failed
- RUNNING: Node is still executing (async/long-running)
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .blackboard import Blackboard


class NodeStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"


@dataclass
class Node:
    """Base class for all behavior tree nodes."""
    name: str
    children: list["Node"] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    _blackboard: Blackboard | None = None

    def __post_init__(self):
        for child in self.children:
            child._parent = self

    @property
    def blackboard(self) -> Blackboard:
        if self._blackboard is None:
            self._blackboard = Blackboard()
        return self._blackboard

    @blackboard.setter
    def blackboard(self, bb: Blackboard):
        self._blackboard = bb
        for child in self.children:
            child.blackboard = bb

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        """Execute one tick of this node. Override in subclasses."""
        if blackboard:
            self.blackboard = blackboard
        return NodeStatus.FAILURE

    def reset(self) -> None:
        """Reset node state for re-execution."""
        for child in self.children:
            child.reset()

    def add_child(self, child: "Node") -> "Node":
        child._parent = self
        self.children.append(child)
        if self._blackboard:
            child.blackboard = self._blackboard
        return self

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class Composite(Node):
    """Base class for nodes with children (Sequence, Selector, Parallel)."""
    def __init__(self, name: str, children: list[Node] | None = None, **properties):
        super().__init__(name, children or [], properties)
        self._current_child_index = 0

    def reset(self) -> None:
        super().reset()
        self._current_child_index = 0


class Sequence(Composite):
    """
    Sequence: Execute children in order.
    - Returns SUCCESS if all children return SUCCESS
    - Returns FAILURE if any child returns FAILURE
    - Returns RUNNING if any child returns RUNNING (pauses there)
    """

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        while self._current_child_index < len(self.children):
            child = self.children[self._current_child_index]
            status = child.tick(blackboard)

            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            elif status == NodeStatus.FAILURE:
                self._current_child_index = 0
                return NodeStatus.FAILURE
            elif status == NodeStatus.SUCCESS:
                self._current_child_index += 1

        self._current_child_index = 0
        return NodeStatus.SUCCESS


class Selector(Composite):
    """
    Selector (Fallback): Try children in order until one succeeds.
    - Returns SUCCESS if any child returns SUCCESS
    - Returns FAILURE if all children return FAILURE
    - Returns RUNNING if any child returns RUNNING (pauses there)
    """

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        while self._current_child_index < len(self.children):
            child = self.children[self._current_child_index]
            status = child.tick(blackboard)

            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            elif status == NodeStatus.SUCCESS:
                self._current_child_index = 0
                return NodeStatus.SUCCESS
            elif status == NodeStatus.FAILURE:
                self._current_child_index += 1

        self._current_child_index = 0
        return NodeStatus.FAILURE


class Parallel(Composite):
    """
    Parallel: Run all children simultaneously.
    - success_threshold: how many must succeed for overall SUCCESS
    - failure_threshold: how many must fail for overall FAILURE
    """

    def __init__(
        self,
        name: str,
        children: list[Node] | None = None,
        success_threshold: int | None = None,
        failure_threshold: int | None = None,
        **properties
    ):
        super().__init__(name, children, **properties)
        self.success_threshold = success_threshold or len(children) if children else 1
        self.failure_threshold = failure_threshold or 1

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        if not self.children:
            return NodeStatus.SUCCESS

        success_count = 0
        failure_count = 0
        running_count = 0

        for child in self.children:
            status = child.tick(blackboard)

            if status == NodeStatus.SUCCESS:
                success_count += 1
            elif status == NodeStatus.FAILURE:
                failure_count += 1
            elif status == NodeStatus.RUNNING:
                running_count += 1

        # Check success first (standard BT behavior)
        if success_count >= self.success_threshold:
            return NodeStatus.SUCCESS
        if failure_count >= self.failure_threshold:
            return NodeStatus.FAILURE
        return NodeStatus.RUNNING


class Action(Node):
    """
    Action: Leaf node that performs a task.
    Can be synchronous (function) or async (generator/coroutine).
    """

    def __init__(
        self,
        name: str,
        func: Callable[..., NodeStatus] | None = None,
        **properties
    ):
        super().__init__(name, properties=properties)
        self._func = func or (lambda bb: NodeStatus.SUCCESS)
        self._running = False

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        try:
            result = self._func(self.blackboard)
            if isinstance(result, NodeStatus):
                return result
            return NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        except Exception as e:
            self.blackboard.set(f"{self.name}_error", str(e))
            return NodeStatus.FAILURE

    def reset(self) -> None:
        self._running = False
        super().reset()


class Condition(Node):
    """
    Condition: Leaf node that checks a condition.
    Returns SUCCESS or FAILURE (never RUNNING).
    """

    def __init__(
        self,
        name: str,
        func: Callable[..., bool] | None = None,
        **properties
    ):
        super().__init__(name, properties=properties)
        self._func = func or (lambda bb: True)

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        try:
            result = self._func(self.blackboard)
            return NodeStatus.SUCCESS if result else NodeStatus.FAILURE
        except Exception:
            return NodeStatus.FAILURE


class Decorator(Node):
    """
    Decorator: Single child, modifies behavior.
    Base class for Inverter, Repeater, UntilSuccess, Timeout, etc.
    """

    def __init__(self, name: str, child: Node | None = None, **properties):
        super().__init__(name, [child] if child else [], properties)

    @property
    def child(self) -> Node | None:
        return self.children[0] if self.children else None

    @child.setter
    def child(self, node: Node):
        if self.children:
            self.children[0] = node
        else:
            self.children.append(node)
        node._parent = self


class Inverter(Decorator):
    """Invert child's result: SUCCESS <-> FAILURE, RUNNING stays RUNNING."""

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        if not self.child:
            return NodeStatus.FAILURE

        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        elif status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return NodeStatus.RUNNING


class Repeater(Decorator):
    """Repeat child N times or until failure."""

    def __init__(
        self,
        name: str,
        child: Node | None = None,
        count: int = -1,  # -1 = infinite
        **properties
    ):
        super().__init__(name, child, **properties)
        self.count = count
        self._current_count = 0

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        if not self.child:
            return NodeStatus.FAILURE

        if self.count != -1 and self._current_count >= self.count:
            return NodeStatus.SUCCESS

        status = self.child.tick(blackboard)

        if status == NodeStatus.RUNNING:
            return NodeStatus.RUNNING

        self._current_count += 1

        if status == NodeStatus.FAILURE:
            self._current_count = 0
            return NodeStatus.FAILURE

        if self.count != -1 and self._current_count >= self.count:
            self._current_count = 0
            return NodeStatus.SUCCESS

        self.child.reset()
        return NodeStatus.RUNNING

    def reset(self) -> None:
        self._current_count = 0
        super().reset()


class UntilSuccess(Decorator):
    """Keep running child until it returns SUCCESS."""

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        if not self.child:
            return NodeStatus.FAILURE

        status = self.child.tick(blackboard)

        if status == NodeStatus.SUCCESS:
            return NodeStatus.SUCCESS

        if status == NodeStatus.RUNNING:
            return NodeStatus.RUNNING

        self.child.reset()
        return NodeStatus.RUNNING


class Timeout(Decorator):
    """Fail if child runs longer than timeout ticks."""

    def __init__(
        self,
        name: str,
        child: Node | None = None,
        max_ticks: int = 100,
        **properties
    ):
        super().__init__(name, child, **properties)
        self.max_ticks = max_ticks
        self._tick_count = 0

    def tick(self, blackboard: Blackboard | None = None) -> NodeStatus:
        if blackboard:
            self.blackboard = blackboard

        if not self.child:
            return NodeStatus.FAILURE

        self._tick_count += 1

        if self._tick_count >= self.max_ticks:
            self._tick_count = 0
            return NodeStatus.FAILURE

        status = self.child.tick(blackboard)

        if status != NodeStatus.RUNNING:
            self._tick_count = 0

        return status

    def reset(self) -> None:
        self._tick_count = 0
        super().reset()
