"""
Behavior Tree Library
A Python implementation of behavior trees for robotics and game AI.
"""

from .blackboard import Blackboard
from .nodes import Action, Condition, Decorator, Node, Selector, Sequence
from .parser import (
    node_to_dict,
    node_to_xml,
    parse_auto,
    parse_json,
    parse_json_file,
    parse_string,
    parse_xml,
    parse_xml_file,
    parse_yaml,
    parse_yaml_file,
)
from .tree import BehaviorTree

__all__ = [
    "Node",
    "Sequence",
    "Selector",
    "Action",
    "Condition",
    "Decorator",
    "Blackboard",
    "BehaviorTree",
    "parse_xml",
    "parse_xml_file",
    "parse_json",
    "parse_json_file",
    "parse_yaml",
    "parse_yaml_file",
    "parse_auto",
    "parse_string",
    "node_to_dict",
    "node_to_xml",
]

__version__ = "0.1.0"
