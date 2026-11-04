"""
Tests for behavior tree node classes.
"""

import pytest

from bt_lib.blackboard import Blackboard
from bt_lib.nodes import (
    Action,
    Condition,
    Inverter,
    NodeStatus,
    Parallel,
    Repeater,
    Selector,
    Sequence,
    Timeout,
    UntilSuccess,
)


class TestNodeStatus:
    def test_status_values(self):
        assert NodeStatus.SUCCESS.value == "SUCCESS"
        assert NodeStatus.FAILURE.value == "FAILURE"
        assert NodeStatus.RUNNING.value == "RUNNING"


class TestBlackboard:
    def test_basic_set_get(self):
        bb = Blackboard()
        bb.set("key", "value")
        assert bb.get("key") == "value"

    def test_default_value(self):
        bb = Blackboard()
        assert bb.get("missing", "default") == "default"

    def test_hierarchical_inheritance(self):
        parent = Blackboard()
        parent.set("parent_key", "parent_value")
        child = parent.child()
        assert child.get("parent_key") == "parent_value"

    def test_child_write_is_local(self):
        parent = Blackboard()
        parent.set("key", "parent")
        child = parent.child()
        child.set("key", "child")
        assert child.get("key") == "child"
        assert parent.get("key") == "parent"

    def test_contains(self):
        bb = Blackboard()
        bb.set("key", "value")
        assert "key" in bb
        assert "missing" not in bb

    def test_dict_access(self):
        bb = Blackboard()
        bb["key"] = "value"
        assert bb["key"] == "value"

    def test_to_dict(self):
        parent = Blackboard()
        parent.set("parent_key", "parent_value")
        child = parent.child()
        child.set("child_key", "child_value")
        d = child.to_dict()
        assert d["parent_key"] == "parent_value"
        assert d["child_key"] == "child_value"


class TestSequence:
    def test_empty_sequence_succeeds(self):
        seq = Sequence("empty")
        bb = Blackboard()
        assert seq.tick(bb) == NodeStatus.SUCCESS

    def test_all_success(self):
        seq = Sequence("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.SUCCESS),
        ])
        bb = Blackboard()
        assert seq.tick(bb) == NodeStatus.SUCCESS

    def test_failure_stops(self):
        seq = Sequence("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.FAILURE),
            Action("a3", lambda bb: NodeStatus.SUCCESS),
        ])
        bb = Blackboard()
        assert seq.tick(bb) == NodeStatus.FAILURE

    def test_running_pauses(self):
        seq = Sequence("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.RUNNING),
            Action("a3", lambda bb: NodeStatus.SUCCESS),
        ])
        bb = Blackboard()
        assert seq.tick(bb) == NodeStatus.RUNNING
        assert seq.tick(bb) == NodeStatus.RUNNING

    def test_reset_clears_state(self):
        seq = Sequence("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.FAILURE),
        ])
        bb = Blackboard()
        seq.tick(bb)
        seq.reset()
        # After reset, should start from first child again
        seq.tick(bb)  # a1 succeeds
        assert seq.tick(bb) == NodeStatus.FAILURE  # a2 fails


class TestSelector:
    def test_empty_selector_fails(self):
        sel = Selector("empty")
        bb = Blackboard()
        assert sel.tick(bb) == NodeStatus.FAILURE

    def test_first_success(self):
        sel = Selector("test", children=[
            Action("a1", lambda bb: NodeStatus.FAILURE),
            Action("a2", lambda bb: NodeStatus.SUCCESS),
            Action("a3", lambda bb: NodeStatus.SUCCESS),
        ])
        bb = Blackboard()
        assert sel.tick(bb) == NodeStatus.SUCCESS

    def test_all_fail(self):
        sel = Selector("test", children=[
            Action("a1", lambda bb: NodeStatus.FAILURE),
            Action("a2", lambda bb: NodeStatus.FAILURE),
        ])
        bb = Blackboard()
        assert sel.tick(bb) == NodeStatus.FAILURE

    def test_running_pauses(self):
        sel = Selector("test", children=[
            Action("a1", lambda bb: NodeStatus.FAILURE),
            Action("a2", lambda bb: NodeStatus.RUNNING),
        ])
        bb = Blackboard()
        assert sel.tick(bb) == NodeStatus.RUNNING


class TestParallel:
    def test_all_succeed(self):
        par = Parallel("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.SUCCESS),
        ], success_threshold=2)
        bb = Blackboard()
        assert par.tick(bb) == NodeStatus.SUCCESS

    def test_threshold_success(self):
        par = Parallel("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.FAILURE),
            Action("a3", lambda bb: NodeStatus.SUCCESS),
        ], success_threshold=2)
        bb = Blackboard()
        assert par.tick(bb) == NodeStatus.SUCCESS

    def test_failure_threshold(self):
        par = Parallel("test", children=[
            Action("a1", lambda bb: NodeStatus.SUCCESS),
            Action("a2", lambda bb: NodeStatus.FAILURE),
        ], failure_threshold=1)
        bb = Blackboard()
        assert par.tick(bb) == NodeStatus.FAILURE


class TestAction:
    def test_success_action(self):
        action = Action("test", lambda bb: NodeStatus.SUCCESS)
        bb = Blackboard()
        assert action.tick(bb) == NodeStatus.SUCCESS

    def test_failure_action(self):
        action = Action("test", lambda bb: NodeStatus.FAILURE)
        bb = Blackboard()
        assert action.tick(bb) == NodeStatus.FAILURE

    def test_running_action(self):
        action = Action("test", lambda bb: NodeStatus.RUNNING)
        bb = Blackboard()
        assert action.tick(bb) == NodeStatus.RUNNING

    def test_bool_return(self):
        action = Action("test", lambda bb: True)
        bb = Blackboard()
        assert action.tick(bb) == NodeStatus.SUCCESS

        action2 = Action("test2", lambda bb: False)
        assert action2.tick(bb) == NodeStatus.FAILURE

    def test_exception_handled(self):
        action = Action("test", lambda bb: (_ for _ in ()).throw(Exception("fail")))
        bb = Blackboard()
        assert action.tick(bb) == NodeStatus.FAILURE


class TestCondition:
    def test_true_condition(self):
        cond = Condition("test", lambda bb: True)
        bb = Blackboard()
        assert cond.tick(bb) == NodeStatus.SUCCESS

    def test_false_condition(self):
        cond = Condition("test", lambda bb: False)
        bb = Blackboard()
        assert cond.tick(bb) == NodeStatus.FAILURE

    def test_blackboard_access(self):
        cond = Condition("test", lambda bb: bb.get("key") == "value")
        bb = Blackboard()
        bb.set("key", "value")
        assert cond.tick(bb) == NodeStatus.SUCCESS


class TestDecorators:
    def test_inverter(self):
        inv = Inverter("inv", child=Action("child", lambda bb: NodeStatus.SUCCESS))
        bb = Blackboard()
        assert inv.tick(bb) == NodeStatus.FAILURE

        inv2 = Inverter("inv2", child=Action("child", lambda bb: NodeStatus.FAILURE))
        assert inv2.tick(bb) == NodeStatus.SUCCESS

        inv3 = Inverter("inv3", child=Action("child", lambda bb: NodeStatus.RUNNING))
        assert inv3.tick(bb) == NodeStatus.RUNNING

    def test_repeater_finite(self):
        count = 0
        def action(bb):
            nonlocal count
            count += 1
            return NodeStatus.SUCCESS

        rep = Repeater("rep", child=Action("child", action), count=3)
        bb = Blackboard()
        assert rep.tick(bb) == NodeStatus.RUNNING
        assert rep.tick(bb) == NodeStatus.RUNNING
        assert rep.tick(bb) == NodeStatus.SUCCESS
        assert count == 3

    def test_repeater_infinite(self):
        count = 0
        def action(bb):
            nonlocal count
            count += 1
            return NodeStatus.SUCCESS

        rep = Repeater("rep", child=Action("child", action), count=-1)
        bb = Blackboard()
        for _ in range(5):
            assert rep.tick(bb) == NodeStatus.RUNNING
        assert count == 5

    def test_repeater_stops_on_failure(self):
        rep = Repeater("rep", child=Action("child", lambda bb: NodeStatus.FAILURE), count=3)
        bb = Blackboard()
        assert rep.tick(bb) == NodeStatus.FAILURE

    def test_until_success(self):
        count = 0
        def action(bb):
            nonlocal count
            count += 1
            return NodeStatus.SUCCESS if count >= 3 else NodeStatus.FAILURE

        unt = UntilSuccess("unt", child=Action("child", action))
        bb = Blackboard()
        assert unt.tick(bb) == NodeStatus.RUNNING
        assert unt.tick(bb) == NodeStatus.RUNNING
        assert unt.tick(bb) == NodeStatus.SUCCESS
        assert count == 3

    def test_timeout(self):
        def running_action(bb):
            return NodeStatus.RUNNING

        timeout = Timeout("timeout", child=Action("child", running_action), max_ticks=3)
        bb = Blackboard()
        assert timeout.tick(bb) == NodeStatus.RUNNING
        assert timeout.tick(bb) == NodeStatus.RUNNING
        assert timeout.tick(bb) == NodeStatus.FAILURE


class TestNodeHierarchy:
    def test_add_child(self):
        seq = Sequence("parent")
        action = Action("child")
        seq.add_child(action)
        assert len(seq.children) == 1
        assert action._parent is seq

    def test_blackboard_propagation(self):
        seq = Sequence("parent", children=[Action("child")])
        bb = Blackboard()
        bb.set("test", "value")
        seq.blackboard = bb
        assert seq.children[0].blackboard is bb


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
