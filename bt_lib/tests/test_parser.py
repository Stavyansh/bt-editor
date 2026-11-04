"""
Tests for behavior tree parser (XML, JSON, YAML).
"""

import os
import tempfile

import pytest

from bt_lib.nodes import Action, Sequence
from bt_lib.parser import (
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


class TestXMLParser:
    def test_simple_sequence(self):
        xml = '<Sequence name="Test"><Action name="A1"/><Action name="A2"/></Sequence>'
        root = parse_xml(xml)
        assert root.name == "Test"
        assert type(root).__name__ == "Sequence"
        assert len(root.children) == 2
        assert all(type(c).__name__ == "Action" for c in root.children)

    def test_nested_structure(self):
        xml = '''
        <Selector name="Root">
            <Sequence name="Seq1">
                <Condition name="Cond1"/>
                <Action name="Act1"/>
            </Sequence>
            <Action name="Fallback"/>
        </Selector>
        '''
        root = parse_xml(xml)
        assert root.name == "Root"
        assert type(root).__name__ == "Selector"
        assert len(root.children) == 2
        assert root.children[0].name == "Seq1"
        assert root.children[1].name == "Fallback"

    def test_properties(self):
        xml = '<Repeater name="Rep" count="5"><Action name="Act"/></Repeater>'
        root = parse_xml(xml)
        assert root.count == 5

    def test_self_closing_tags(self):
        xml = '<Sequence><Action name="A1"/><Action name="A2"/></Sequence>'
        root = parse_xml(xml)
        assert len(root.children) == 2

    def test_mixed_self_closing_and_open(self):
        xml = '<Sequence><Action name="A1"/><Action name="A2"></Action></Sequence>'
        root = parse_xml(xml)
        assert len(root.children) == 2

    def test_file_parsing(self):
        xml = '<Sequence name="FileTest"><Action name="A"/></Sequence>'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml)
            fname = f.name
        try:
            root = parse_xml_file(fname)
            assert root.name == "FileTest"
        finally:
            os.unlink(fname)


class TestJSONParser:
    def test_simple_sequence(self):
        json_str = '{"type": "Sequence", "name": "Test", "children": [{"type": "Action", "name": "A1"}, {"type": "Action", "name": "A2"}]}'
        root = parse_json(json_str)
        assert root.name == "Test"
        assert type(root).__name__ == "Sequence"
        assert len(root.children) == 2

    def test_properties(self):
        json_str = '{"type": "Repeater", "name": "Rep", "properties": {"count": 3}, "children": [{"type": "Action", "name": "Act"}]}'
        root = parse_json(json_str)
        assert root.count == 3

    def test_file_parsing(self):
        json_str = '{"type": "Sequence", "name": "FileTest", "children": []}'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_str)
            fname = f.name
        try:
            root = parse_json_file(fname)
            assert root.name == "FileTest"
        finally:
            os.unlink(fname)


class TestYAMLParser:
    def test_simple_sequence(self):
        yaml_str = """
        type: Sequence
        name: Test
        children:
          - type: Action
            name: A1
          - type: Action
            name: A2
        """
        root = parse_yaml(yaml_str)
        assert root.name == "Test"
        assert type(root).__name__ == "Sequence"
        assert len(root.children) == 2

    def test_properties(self):
        yaml_str = """
        type: Repeater
        name: Rep
        properties:
          count: 5
        children:
          - type: Action
            name: Act
        """
        root = parse_yaml(yaml_str)
        assert root.count == 5

    def test_file_parsing(self):
        yaml_str = "type: Sequence\nname: FileTest\nchildren: []\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_str)
            fname = f.name
        try:
            root = parse_yaml_file(fname)
            assert root.name == "FileTest"
        finally:
            os.unlink(fname)


class TestAutoParser:
    def test_xml_extension(self):
        xml = '<Sequence name="Auto"><Action name="A"/></Sequence>'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml)
            fname = f.name
        try:
            root = parse_auto(fname)
            assert root.name == "Auto"
        finally:
            os.unlink(fname)

    def test_json_extension(self):
        json_str = '{"type": "Sequence", "name": "Auto", "children": []}'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_str)
            fname = f.name
        try:
            root = parse_auto(fname)
            assert root.name == "Auto"
        finally:
            os.unlink(fname)

    def test_yaml_extension(self):
        yaml_str = "type: Sequence\nname: Auto\nchildren: []\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_str)
            fname = f.name
        try:
            root = parse_auto(fname)
            assert root.name == "Auto"
        finally:
            os.unlink(fname)


class TestParseString:
    def test_xml_format(self):
        xml = '<Sequence name="Str"><Action name="A"/></Sequence>'
        root = parse_string(xml, "xml")
        assert root.name == "Str"

    def test_json_format(self):
        json_str = '{"type": "Sequence", "name": "Str", "children": []}'
        root = parse_string(json_str, "json")
        assert root.name == "Str"

    def test_yaml_format(self):
        yaml_str = "type: Sequence\nname: Str\nchildren: []\n"
        root = parse_string(yaml_str, "yaml")
        assert root.name == "Str"


class TestSerialization:
    def test_node_to_dict(self):
        seq = Sequence("Test", children=[Action("A1"), Action("A2")])
        d = node_to_dict(seq)
        assert d["type"] == "Sequence"
        assert d["name"] == "Test"
        assert len(d["children"]) == 2

    def test_node_to_xml(self):
        seq = Sequence("Test", children=[Action("A1")])
        xml = node_to_xml(seq)
        assert "Sequence" in xml
        assert "Test" in xml
        assert "Action" in xml
        assert "A1" in xml

    def test_roundtrip_xml(self):
        original = '<Sequence name="RT"><Action name="A1"/><Action name="A2"/></Sequence>'
        root = parse_xml(original)
        xml = node_to_xml(root)
        root2 = parse_xml(xml)
        assert root2.name == "RT"
        assert len(root2.children) == 2


class TestExampleFiles:
    def test_simple_xml(self):
        root = parse_xml_file("examples/simple.xml")
        assert root.name == "SimpleSequence"
        assert len(root.children) == 3

    def test_patrol_xml(self):
        root = parse_xml_file("examples/patrol.xml")
        assert root.name == "RobotPatrol"
        assert type(root).__name__ == "Selector"
        assert len(root.children) == 3

    def test_pickup_xml(self):
        root = parse_xml_file("examples/pickup.xml")
        assert root.name == "PickAndPlace"
        assert type(root).__name__ == "Sequence"
        assert len(root.children) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
