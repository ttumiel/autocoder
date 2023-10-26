from dataclasses import dataclass, field

import pytest

from chat2func import json_schema


def bare_function(arg1, arg2):
    return arg1 == int(arg2)


def function_with_types(arg1: int, arg2: str) -> bool:
    return arg1 == int(arg2)


def function_with_docstring(arg1, arg2):
    """Tests for equivalence. More description.

    Long description.

    Args:
        arg1 (int): First argument
        arg2 (str): Second argument

    Returns:
        True if equivalent
    """
    return arg1 == int(arg2)


def function_with_docstring_and_types(arg1: int, arg2: str, arg3: float = 0.0) -> bool:
    """Tests for equivalence

    Args:
        arg1 (int): First argument
        arg2 (str): Second argument
        arg3 (float, optional): Third argument

    Returns:
        True if equivalent
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
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {"application/json": {"schema": {"type": "boolean"}}},
                    }
                },
            },
        ),
        (
            function_with_docstring,
            True,
            {
                "name": "function_with_docstring",
                "description": "Tests for equivalence. More description.\nLong description.",
                "parameters": {
                    "type": "object",
                    "required": ["arg1", "arg2"],
                    "properties": {
                        "arg1": {"type": "integer", "description": "First argument"},
                        "arg2": {"type": "string", "description": "Second argument"},
                    },
                },
                "responses": {"200": {"description": "True if equivalent"}},
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
                        "arg3": {"type": "number", "description": "Third argument", "default": 0.0},
                    },
                },
                "responses": {
                    "200": {
                        "description": "True if equivalent",
                        "content": {"application/json": {"schema": {"type": "boolean"}}},
                    }
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
                        "c": {"type": "boolean", "default": False},
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
                        "a": {"type": "integer", "default": 0},
                        "b": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "integer"},
                                "b": {"type": "string"},
                                "c": {"type": "boolean", "default": False},
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
    assert (
        json_schema(function, descriptions=parse_description, full_docstring=True).__schema__
        == expected
    )
