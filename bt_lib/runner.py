"""
Tree Runner - Execute behavior trees from files with CLI output.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from .parser import parse_auto
from .tree import BehaviorTree
from .nodes import NodeStatus
from .blackboard import Blackboard


def run_tree_file(
    filepath: str,
    max_ticks: int = 1000,
    tick_delay: float = 0.0,
    verbose: bool = False,
    initial_blackboard: Optional[dict] = None
) -> NodeStatus:
    """
    Run a behavior tree from file.

    Args:
        filepath: Path to XML/JSON/YAML tree file
        max_ticks: Maximum ticks before timeout
        tick_delay: Delay between ticks (seconds)
        verbose: Print detailed tick information
        initial_blackboard: Initial blackboard values

    Returns:
        Final NodeStatus
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Tree file not found: {filepath}")

    root = parse_auto(path)
    tree = BehaviorTree(root, name=path.stem)

    if initial_blackboard:
        for key, value in initial_blackboard.items():
            tree.set_blackboard(key, value)

    if verbose:
        print(f"Running tree: {tree.name}")
        print(f"Root: {tree.root.name} ({type(tree.root).__name__})")
        print(f"Max ticks: {max_ticks}")
        print("-" * 50)

    for tick_num in range(1, max_ticks + 1):
        status = tree.tick_once()

        if verbose:
            bb = tree.blackboard.to_dict()
            bb_str = ", ".join(f"{k}={v}" for k, v in bb.items()) if bb else "empty"
            print(f"Tick {tick_num:3d}: {status.value:9s} | Blackboard: {{{bb_str}}}")

        if tick_delay > 0:
            time.sleep(tick_delay)

        if status != NodeStatus.RUNNING:
            if verbose:
                print("-" * 50)
                print(f"Final status: {status.value} (after {tick_num} ticks)")
            return status

    if verbose:
        print("-" * 50)
        print(f"Max ticks ({max_ticks}) reached. Final status: {NodeStatus.RUNNING.value}")
    return NodeStatus.RUNNING


def run_tree_string(
    xml_string: str,
    max_ticks: int = 1000,
    tick_delay: float = 0.0,
    verbose: bool = False,
    initial_blackboard: Optional[dict] = None
) -> NodeStatus:
    """Run a behavior tree from XML string."""
    from .parser import parse_xml
    root = parse_xml(xml_string)
    tree = BehaviorTree(root, name="StringTree")

    if initial_blackboard:
        for key, value in initial_blackboard.items():
            tree.set_blackboard(key, value)

    for tick_num in range(1, max_ticks + 1):
        status = tree.tick_once()

        if verbose:
            bb = tree.blackboard.to_dict()
            bb_str = ", ".join(f"{k}={v}" for k, v in bb.items()) if bb else "empty"
            print(f"Tick {tick_num:3d}: {status.value:9s} | Blackboard: {{{bb_str}}}")

        if tick_delay > 0:
            time.sleep(tick_delay)

        if status != NodeStatus.RUNNING:
            return status

    return NodeStatus.RUNNING


def print_tree_structure(node, indent: int = 0, show_properties: bool = True):
    """Print tree structure for debugging."""
    prefix = "  " * indent
    props = ""
    if show_properties and node.properties:
        props = f" [{', '.join(f'{k}={v}' for k, v in node.properties.items())}]"
    print(f"{prefix}{type(node).__name__}: {node.name}{props}")

    for child in node.children:
        print_tree_structure(child, indent + 1, show_properties)


def main():
    parser = argparse.ArgumentParser(
        description="Behavior Tree Runner - Execute BT from XML/JSON/YAML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m bt_lib.runner examples/simple.xml
  python -m bt_lib.runner examples/patrol.xml --verbose --max-ticks 50
  python -m bt_lib.runner examples/pickup.xml --tick-delay 0.5 --verbose
  python -m bt_lib.runner examples/simple.xml --blackboard battery=20 dirt=true
        """
    )

    parser.add_argument("file", help="Path to tree file (XML, JSON, or YAML)")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed tick-by-tick output"
    )
    parser.add_argument(
        "-m", "--max-ticks",
        type=int,
        default=1000,
        help="Maximum ticks before timeout (default: 1000)"
    )
    parser.add_argument(
        "-d", "--tick-delay",
        type=float,
        default=0.0,
        help="Delay between ticks in seconds (default: 0)"
    )
    parser.add_argument(
        "-b", "--blackboard",
        action="append",
        help="Initial blackboard values as key=value (can repeat)"
    )
    parser.add_argument(
        "--show-tree",
        action="store_true",
        help="Print tree structure and exit"
    )

    args = parser.parse_args()

    # Parse blackboard args
    initial_bb = {}
    if args.blackboard:
        for item in args.blackboard:
            if "=" in item:
                key, value = item.split("=", 1)
                # Try to parse value
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                initial_bb[key] = value

    try:
        if args.show_tree:
            root = parse_auto(args.file)
            print_tree_structure(root)
            return 0

        status = run_tree_file(
            args.file,
            max_ticks=args.max_ticks,
            tick_delay=args.tick_delay,
            verbose=args.verbose,
            initial_blackboard=initial_bb if initial_bb else None
        )

        # Exit code based on status
        if status == NodeStatus.SUCCESS:
            return 0
        elif status == NodeStatus.FAILURE:
            return 1
        else:
            return 2  # RUNNING (timeout)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())