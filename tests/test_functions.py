import json
from typing import Any, List, Optional

import pytest

from chat2func import FunctionCallError, function_call


class ClassTest:
    def __init__(self, a: int):
        self.a = a


@pytest.fixture
def test_function():
    def test(a: int, b: bool = False) -> bool:
        return a > 0 and b

    return test


@pytest.fixture
def test_function_2():
    def test(
        a, b: Any, c: ClassTest, d: List[int], e: Optional[str], f: Optional[int] = None
    ) -> bool:
        assert isinstance(c, ClassTest)
        assert isinstance(e, (type(None), str))
        return True

    return test


def test_working_function_call(test_function, call_builder):
    call = call_builder(test_function)
    assert call(json.dumps({"a": 1})) == "false"
    assert call(json.dumps({"a": 1, "b": True})) == "true"
    assert call(json.dumps({"a": -1, "b": True})) == "false"


def test_working_function_call(test_function_2, call_builder):
    call = call_builder(test_function_2, from_json=False, return_json=False, validate=False)
    assert call({"a": 1, "b": 2, "c": {"a": 3}, "d": [1, 2, 3], "e": None})
    assert call({"a": 1, "b": 2, "c": {"a": 3}, "d": [1, 2, 3], "e": "test", "f": 4})


def test_function_call_with_wrong_parameters(test_function, call_builder):
    call = call_builder(test_function)

    with pytest.raises(FunctionCallError):
        call(json.dumps({"b": True}))

    with pytest.raises(FunctionCallError):
        call(json.dumps({"a": 1, "b": True, "c": 7}))

    with pytest.raises(FunctionCallError):
        call(json.dumps({"a": "a", "b": False}))


def test_missing_function(test_function):
    with pytest.raises(FunctionCallError):
        function_call("t", json.dumps({"a": 1}), {"test": test_function})


def test_class_call(call_builder):
    call = call_builder(ClassTest, return_json=False, validate=False)

    assert isinstance(call(json.dumps({"a": 1})), ClassTest)
