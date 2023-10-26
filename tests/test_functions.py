import json
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import pytest

from chat2func import FunctionCallError, function_call, json_schema
from chat2func.schema import schema_to_type


class ClassTest:
    def __init__(self, a: int):
        self.a = a


class MyEnum(Enum):
    A = "a"
    B = "b"


@pytest.fixture
def test_function():
    def test(a: int, b: bool = False, my_enum: MyEnum = MyEnum.A) -> bool:
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


@pytest.fixture
def test_function_3():
    def test(a: int, b: Dict[str, ClassTest]) -> bool:
        assert all(isinstance(v, ClassTest) for v in b.values())
        assert all(isinstance(v, str) for v in b.keys())
        assert isinstance(a, int)
        return True

    return test


@pytest.fixture
def test_function_4():
    def test() -> bool:
        assert False

    return test


def test_working_function_call(test_function, call_builder):
    call = call_builder(test_function)
    assert call(json.dumps({"a": 1})) == "false"
    assert call(json.dumps({"a": 1, "b": True})) == "true"
    assert call(json.dumps({"a": -1, "b": True})) == "false"
    assert call(json.dumps({"a": 1, "b": True, "my_enum": "b"})) == "true"


def test_working_function_call_2(test_function_2, call_builder):
    call = call_builder(test_function_2, from_json=False, return_json=False, validate=False)
    assert call({"a": 1, "b": 2, "c": {"a": 3}, "d": [1, 2, 3], "e": None})
    assert call({"a": 1, "b": 2, "c": {"a": 3}, "d": [1, 2, 3], "e": "test", "f": 4})


def test_working_function_call_3(test_function_3, call_builder):
    call = call_builder(test_function_3, return_json=False, validate=False)
    assert call(json.dumps({"a": 1, "b": {"one": {"a": 3}, "two": {"a": 4}}}))
    assert call(json.dumps({"a": 1, "b": {}}))


def test_function_call_with_wrong_schema(test_function, call_builder):
    call = call_builder(test_function)
    ERROR = "Arguments do not match the schema."

    with pytest.raises(FunctionCallError, match=ERROR):
        call(json.dumps({"a": 1, "b": 1}))

    with pytest.raises(FunctionCallError, match=ERROR):
        call(json.dumps({"a": False, "b": True}))

    with pytest.raises(FunctionCallError, match=ERROR):
        call(json.dumps({"b": True}))

    with pytest.raises(FunctionCallError, match=ERROR):
        call(json.dumps({"a": "a", "b": False}))

    with pytest.raises(FunctionCallError, match=ERROR):
        call(json.dumps({"a": 1, "b": True, "my_enum": "d"}))


def test_function_call_with_wrong_parameters(test_function, call_builder):
    call = call_builder(test_function)

    with pytest.raises(FunctionCallError, match="Arguments do not match function signature."):
        call(json.dumps({"a": 1, "b": True, "c": 7}))


def test_missing_function(test_function):
    with pytest.raises(FunctionCallError, match="Function `t` not found."):
        function_call("t", json.dumps({"a": 1}), {"test": test_function})


def test_invalid_json_function(test_function):
    with pytest.raises(FunctionCallError, match="Arguments are not valid JSON."):
        function_call("test", '{"a: 1}', {"test": test_function})


def test_function_error(test_function_4, call_builder):
    call = call_builder(test_function_4)

    with pytest.raises(FunctionCallError, match="Function call failed."):
        call("{}")


def test_class_call(call_builder):
    call = call_builder(ClassTest, return_json=False)

    assert isinstance(call(json.dumps({"a": 1})), ClassTest)


@json_schema
class PydanticSchemaTest:
    def __init__(self, a: int):
        self.a = a


def test_pydantic_schema():
    @json_schema
    def f(a: Sequence[PydanticSchemaTest]):
        return a[0]

    unwrapped_type = PydanticSchemaTest._function
    args, kwargs = schema_to_type(f, {"a": [{"a": 1}]})
    assert len(args) == 1
    assert isinstance(args[0][0], unwrapped_type)
    assert isinstance(f(*args, **kwargs), unwrapped_type)

    args, kwargs = schema_to_type(f, {"a": ({"a": 1}, {"a": 2})})
    assert len(args) == 1
    assert isinstance(args[0][0], unwrapped_type)
    assert isinstance(args[0][1], unwrapped_type)
    assert isinstance(f(*args, **kwargs), unwrapped_type)
