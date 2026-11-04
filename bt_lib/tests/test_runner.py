"""
Tests for behavior tree runner and CLI.
"""

import subprocess
import sys

import pytest

from bt_lib.nodes import NodeStatus
from bt_lib.parser import parse_xml
from bt_lib.runner import print_tree_structure, run_tree_file, run_tree_string
from bt_lib.tree import BehaviorTree


class TestRunner:
    def test_simple_sequence(self):
        status = run_tree_file("examples/simple.xml", verbose=False)
        assert status == NodeStatus.SUCCESS

    def test_patrol_with_battery_low(self):
        status = run_tree_file("examples/patrol.xml", verbose=False, initial_blackboard={"BatteryLow": True})
        assert status == NodeStatus.SUCCESS

    def test_patrol_with_dirt(self):
        status = run_tree_file("examples/patrol.xml", verbose=False, initial_blackboard={"DirtDetected": True})
        assert status == NodeStatus.SUCCESS

    def test_patrol_default_succeeds(self):
        # Conditions default to True, so first sequence (LowBattery) succeeds
        status = run_tree_file("examples/patrol.xml", verbose=False, max_ticks=10)
        assert status == NodeStatus.SUCCESS

    def test_pickup_runs(self):
        status = run_tree_file("examples/pickup.xml", verbose=False, max_ticks=10)
        assert status == NodeStatus.SUCCESS

    def test_max_ticks_timeout(self):
        # Create a tree that runs forever
        # Action without func returns SUCCESS by default, so this won't run forever
        # Use a running action via string
        root = parse_xml('<Sequence><Action name="RunForever" /></Sequence>')
        # Modify the action to always return RUNNING
        root.children[0]._func = lambda bb: NodeStatus.RUNNING
        tree = BehaviorTree(root)
        status = tree.tick(max_ticks=5)
        assert status == NodeStatus.RUNNING

    def test_string_runner(self):
        xml = '<Sequence><Action name="A1"/><Action name="A2"/></Sequence>'
        status = run_tree_string(xml, verbose=False)
        assert status == NodeStatus.SUCCESS

    def test_blackboard_passing(self):
        xml = '<Selector><Sequence><Condition name="Check" /><Action name="Act" /></Sequence></Selector>'
        # Need a condition that checks blackboard
        root = parse_xml(xml)
        root.children[0].children[0]._func = lambda bb: bb.get("flag", False)
        tree = BehaviorTree(root)

        # Without flag
        tree.tick(max_ticks=1)
        assert tree.get_status() == NodeStatus.FAILURE

        # With flag
        tree.reset()
        tree.set_blackboard("flag", True)
        tree.tick(max_ticks=1)
        assert tree.get_status() == NodeStatus.SUCCESS


class TestCLI:
    def test_run_simple(self):
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "examples/simple.xml"],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0

    def test_run_verbose(self):
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "examples/simple.xml", "--verbose"],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0
        assert "SUCCESS" in result.stdout
        assert "Tick" in result.stdout

    def test_show_tree(self):
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "examples/patrol.xml", "--show-tree"],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0
        assert "RobotPatrol" in result.stdout
        assert "Selector" in result.stdout
        assert "LowBattery" in result.stdout

    def test_blackboard_arg(self):
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "examples/patrol.xml", "--blackboard", "BatteryLow=true"],
            capture_output=True, text=True, cwd="."
        )
        assert result.returncode == 0

    def test_exit_codes(self):
        # SUCCESS -> 0
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "examples/simple.xml"],
            capture_output=True, cwd="."
        )
        assert result.returncode == 0

        # FAILURE -> 1 (need a tree that actually fails)
        # Create a simple failing tree using an action that returns FAILURE
        import tempfile
        # Use XML with an action that has a failing function via properties
        # We'll use a Sequence with an action that has no func (defaults to SUCCESS)
        # Better: use a custom failing action via the runner's initial_blackboard isn't supported
        # Simplest: just test that a known-failing tree returns 1
        fail_xml = '''<Sequence name="FailTree">
    <Action name="FailAction" />
</Sequence>'''
        # The action will succeed by default, so we need a different approach
        # Use a Selector with a failing condition
        fail_xml = '''<Selector>
    <Sequence>
        <Condition name="AlwaysFalse" />
        <Action name="Act" />
    </Sequence>
</Selector>'''
        # But Condition defaults to True...
        # The test uses the file, so let's just verify the exit code logic works
        # by using a tree we know fails - we can patch the action at runtime
        # Actually, the simplest is to use a Sequence with an Action that has no children
        # Wait - the Action without func returns SUCCESS
        # Let's use the runner's ability to pass a blackboard... no that's for conditions

        # Best approach: create a minimal tree that fails by using a Selector with no children
        fail_xml = '<Selector name="EmptySelector" />'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(fail_xml)
            fname = f.name
        try:
            result = subprocess.run(
                [sys.executable, "-m", "bt_lib.runner", fname],
                capture_output=True, cwd="."
            )
            # Empty Selector returns FAILURE
            assert result.returncode == 1
        finally:
            import os
            os.unlink(fname)

    def test_nonexistent_file(self):
        result = subprocess.run(
            [sys.executable, "-m", "bt_lib.runner", "nonexistent.xml"],
            capture_output=True, cwd="."
        )
        assert result.returncode == 3


class TestTreeStructure:
    def test_print_tree_structure(self, capsys):
        root = parse_xml('<Sequence name="Test"><Action name="A1"/><Selector><Action name="A2"/></Selector></Sequence>')
        print_tree_structure(root)
        captured = capsys.readouterr()
        assert "Sequence: Test" in captured.out
        assert "Action: A1" in captured.out
        assert "Selector" in captured.out
        assert "Action: A2" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
