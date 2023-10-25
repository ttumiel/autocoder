import json
from dataclasses import dataclass

import pytest

from chat2func import FunctionCallError, function_call, json_schema


def test_quickstart():
    @json_schema
    def my_function(x: float, y: float) -> bool:
        """This is a sample function.

        Args:
            x: The first float.
            y: Another float.
        """
        return x > y

    assert my_function.json == {
        "description": "This is a sample function.",
        "name": "my_function",
        "parameters": {
            "properties": {
                "x": {"description": "The first float.", "type": "number"},
                "y": {"description": "Another float.", "type": "number"},
            },
            "required": ["x", "y"],
            "type": "object",
        },
        "responses": {
            "200": {
                "content": {"application/json": {"schema": {"type": "boolean"}}},
                "description": "OK",
            }
        },
    }

    @json_schema(descriptions=False)
    @dataclass
    class Data:
        a: int = 0

    assert Data.json == {
        "name": "Data",
        "parameters": {"type": "object", "properties": {"a": {"type": "integer", "default": 0}}},
    }


def test_function_calling():
    def plusplus(x: float, y: float) -> float:
        "Add two floats."
        return x + y

    functions = {"plusplus": plusplus}
    arguments = json.dumps({"x": 1.0, "y": 2.0})
    result = function_call("plusplus", arguments, functions)
    assert result == "3.0"

    with pytest.raises(FunctionCallError, match="Arguments do not match the schema."):
        arguments = json.dumps({"x": "a", "y": 2.0})
        result = function_call("plusplus", arguments, functions)
        # FunctionCallError: Function call failed. 1 validation error for plusplus
