"""
XML/JSON/YAML Parser for Behavior Trees.
Converts tree definitions into executable node objects.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from .nodes import (
    Action,
    Condition,
    Inverter,
    Node,
    Parallel,
    Repeater,
    Selector,
    Sequence,
    Timeout,
    UntilSuccess,
)

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


def parse_xml(xml_string: str) -> Node:
    """Parse XML string into a behavior tree root node."""
    root_elem = ET.fromstring(xml_string)
    return _parse_xml_element(root_elem)


def parse_xml_file(filepath: str | Path) -> Node:
    """Parse XML file into a behavior tree root node."""
    tree = ET.parse(filepath)
    return _parse_xml_element(tree.getroot())


def _parse_xml_element(elem: ET.Element) -> Node:
    """Recursively parse XML element into node."""
    node_type = elem.tag
    name = elem.get("name", node_type)
    properties = {}

    for key, value in elem.attrib.items():
        if key != "name":
            properties[key] = _parse_value(value)

    for child_elem in elem:
        if child_elem.tag == "properties":
            for prop_elem in child_elem:
                properties[prop_elem.tag] = _parse_value(prop_elem.text or "", prop_elem.attrib.get("type"))

    cls = NODE_TYPES.get(node_type, Sequence)
    node = cls(name=name, **properties)

    for child_elem in elem:
        if child_elem.tag != "properties":
            child_node = _parse_xml_element(child_elem)
            node.add_child(child_node)

    return node


def parse_json(json_string: str) -> Node:
    """Parse JSON string into a behavior tree root node."""
    data = json.loads(json_string)
    return _parse_dict(data)


def parse_json_file(filepath: str | Path) -> Node:
    """Parse JSON file into a behavior tree root node."""
    with open(filepath) as f:
        data = json.load(f)
    return _parse_dict(data)


def parse_yaml(yaml_string: str) -> Node:
    """Parse YAML string into a behavior tree root node."""
    data = yaml.safe_load(yaml_string)
    return _parse_dict(data)


def parse_yaml_file(filepath: str | Path) -> Node:
    """Parse YAML file into a behavior tree root node."""
    with open(filepath) as f:
        data = yaml.safe_load(f)
    return _parse_dict(data)


def _parse_dict(data: dict[str, Any]) -> Node:
    """Recursively parse dictionary into node."""
    node_type = data.get("type", "Sequence")
    name = data.get("name", node_type)
    properties = data.get("properties", {})
    children_data = data.get("children", [])

    cls = NODE_TYPES.get(node_type, Sequence)
    node = cls(name=name, **properties)

    for child_data in children_data:
        child_node = _parse_dict(child_data)
        node.add_child(child_node)

    return node


def _parse_value(value: str, type_hint: str | None = None) -> Any:
    """Parse string value to appropriate Python type."""
    if type_hint == "int":
        return int(value)
    elif type_hint == "float":
        return float(value)
    elif type_hint == "bool":
        return value.lower() in ("true", "1", "yes", "on")
    elif type_hint == "list":
        return [v.strip() for v in value.split(",")]

    # Auto-detect
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def parse_auto(filepath: str | Path) -> Node:
    """Auto-detect format from extension and parse."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".xml":
        return parse_xml_file(path)
    elif suffix == ".json":
        return parse_json_file(path)
    elif suffix in (".yaml", ".yml"):
        return parse_yaml_file(path)
    else:
        raise ValueError(f"Unknown format: {suffix}")


def parse_string(content: str, format: str = "xml") -> Node:
    """Parse string content with specified format."""
    format = format.lower()
    if format == "xml":
        return parse_xml(content)
    elif format == "json":
        return parse_json(content)
    elif format == "yaml":
        return parse_yaml(content)
    else:
        raise ValueError(f"Unknown format: {format}")


def node_to_dict(node: Node) -> dict[str, Any]:
    """Serialize node tree to dictionary."""
    result = {
        "type": node.__class__.__name__,
        "name": node.name,
        "properties": node.properties,
    }

    if node.children:
        result["children"] = [node_to_dict(child) for child in node.children]

    return result


def node_to_xml(node: Node, indent: int = 0) -> str:
    """Serialize node tree to XML string."""
    spaces = "  " * indent
    attrs = " ".join(f'{k}="{v}"' for k, v in node.properties.items())
    attr_str = f' {attrs}' if attrs else ''
    name_attr = f' name="{node.name}"' if node.name != node.__class__.__name__ else ''

    xml = f"{spaces}<{node.__class__.__name__}{name_attr}{attr_str}>"

    if node.children:
        xml += "\n"
        for child in node.children:
            xml += node_to_xml(child, indent + 1) + "\n"
        xml += f"{spaces}</{node.__class__.__name__}>"
    else:
        xml += f"</{node.__class__.__name__}>"

    return xml
