import json

import pytest

from chat2func import FunctionCallError, function_call


@pytest.fixture
def test_function():
    def test(a: int, b: bool = False) -> bool:
        return a > 0 and b

    return test


def test_working_function_call(test_function):
    assert function_call("test", json.dumps({"a": 1}), {"test": test_function}) == "false"
    assert function_call("test", json.dumps({"a": 1, "b": True}), {"test": test_function}) == "true"
    assert (
        function_call("test", json.dumps({"a": -1, "b": True}), {"test": test_function}) == "false"
    )


def test_function_call_with_wrong_parameters(test_function):
    with pytest.raises(FunctionCallError):
        function_call("test", json.dumps({"b": True}), {"test": test_function})

    with pytest.raises(FunctionCallError):
        function_call("test", json.dumps({"a": 1, "b": True, "c": 7}), {"test": test_function})

    with pytest.raises(FunctionCallError):
        function_call("test", json.dumps({"a": 1, "b": 0.1}), {"test": test_function})


def test_missing_function(test_function):
    with pytest.raises(FunctionCallError):
        function_call("t", json.dumps({"a": 1}), {"test": test_function})
