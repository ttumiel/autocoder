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

    assert my_function.__schema__ == {
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

    assert Data.__schema__ == {
        "name": "Data",
        "parameters": {"type": "object", "properties": {"a": {"type": "integer", "default": 0}}},
    }


def test_function_calling():
    def addition(x: float, y: float) -> float:
        "Add two floats."
        return x + y

    arguments = json.dumps({"x": 1.0, "y": 2.0})
    result = function_call(addition, arguments)
    assert result == "3.0"

    with pytest.raises(FunctionCallError, match="Arguments do not match the schema."):
        arguments = json.dumps({"x": "a", "y": 2.0})
        result = function_call(addition, arguments)
