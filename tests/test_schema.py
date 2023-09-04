from dataclasses import dataclass, field

import pytest

from autocoder import json_schema


def bare_function(arg1, arg2):
    return arg1 == int(arg2)


def function_with_types(arg1: int, arg2: str) -> bool:
    return arg1 == int(arg2)


def function_with_docstring(arg1, arg2):
    """Tests for equivalence

    Args:
        arg1 (int): First argument
        arg2 (str): Second argument

    Returns: True if equivalent
    """
    return arg1 == int(arg2)


def function_with_docstring_and_types(arg1: int, arg2: str) -> bool:
    """Tests for equivalence

    Args:
        arg1 (int): First argument
        arg2 (str): Second argument

    Returns: True if equivalent
    """
    return arg1 == int(arg2)


@dataclass
class SimpleClass:
    a: int
    b: str
    c: bool = False


@dataclass
class NestedClass:
    a: int = 0
    b: SimpleClass = field(default_factory=lambda: SimpleClass(0, "a"))


@pytest.mark.parametrize(
    "function, parse_description, expected",
    [
        (
            bare_function,
            True,
            {
                "name": "bare_function",
                "parameters": {
                    "type": "object",
                    "required": ["arg1", "arg2"],
                    "properties": {"arg1": {}, "arg2": {}},
                },
            },
        ),
        (
            function_with_types,
            True,
            {
                "name": "function_with_types",
                "parameters": {
                    "type": "object",
                    "required": ["arg1", "arg2"],
                    "properties": {"arg1": {"type": "integer"}, "arg2": {"type": "string"}},
                },
            },
        ),
        (
            function_with_docstring,
            True,
            {
                "name": "function_with_docstring",
                "description": "Tests for equivalence",
                "parameters": {
                    "type": "object",
                    "required": ["arg1", "arg2"],
                    "properties": {
                        "arg1": {"type": "integer", "description": "First argument"},
                        "arg2": {"type": "string", "description": "Second argument"},
                    },
                },
            },
        ),
        (
            function_with_docstring_and_types,
            True,
            {
                "name": "function_with_docstring_and_types",
                "description": "Tests for equivalence",
                "parameters": {
                    "type": "object",
                    "required": ["arg1", "arg2"],
                    "properties": {
                        "arg1": {"type": "integer", "description": "First argument"},
                        "arg2": {"type": "string", "description": "Second argument"},
                    },
                },
            },
        ),
        (
            SimpleClass,
            True,
            {
                "name": "SimpleClass",
                "description": "SimpleClass(a: int, b: str, c: bool = False)",
                "parameters": {
                    "type": "object",
                    "required": ["a", "b"],
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "string"},
                        "c": {"type": "boolean"},
                    },
                },
            },
        ),
        (
            NestedClass,
            False,
            {
                "name": "NestedClass",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "integer"},
                                "b": {"type": "string"},
                                "c": {"type": "boolean"},
                            },
                            "required": ["a", "b"],
                        },
                    },
                },
            },
        ),
    ],
)
def test_json_schema(function, parse_description, expected):
    assert json_schema(function, descriptions=parse_description).json == expected
