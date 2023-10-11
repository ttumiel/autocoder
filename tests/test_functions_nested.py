from dataclasses import dataclass
from typing import Optional

import pytest


@dataclass
class A:
    a: int
    b: bool = False


@dataclass
class B:
    a: A
    b: int


@dataclass
class C:
    a: int
    b: Optional["C"] = None


@pytest.fixture
def test_function():
    def test(a: A, b: B, c: int) -> bool:
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(c, int)
        assert isinstance(a.a, int)
        assert isinstance(a.b, bool)
        assert isinstance(b.a, A)
        assert isinstance(b.b, int)
        assert isinstance(b.a.a, int)
        assert isinstance(b.a.b, bool)
        return True

    return test


@pytest.fixture
def test_recursive_function():
    def test(a: C) -> bool:
        print(a, a.b)
        assert isinstance(a, C)
        assert isinstance(a.a, int)
        while a.b is not None:
            assert isinstance(a.a, int)
            assert isinstance(a.b, C)
            a = a.b
        return True

    return test


def test_nested_function_call(test_function, call_builder):
    call = call_builder(test_function, return_json=False, from_json=False)
    assert call({"a": {"a": 1, "b": True}, "b": {"a": {"a": 2, "b": False}, "b": 3}, "c": 4})


def test_recursive_function_call(test_recursive_function, call_builder):
    call = call_builder(test_recursive_function, return_json=False, from_json=False, validate=False)

    assert call({"a": {"a": 1}})
    assert call({"a": {"a": 1, "b": {"a": 2}}})
    assert call({"a": {"a": 1, "b": {"a": 2, "b": {"a": 3}}}})
    assert call({"a": {"a": 1, "b": {"a": 2, "b": {"a": 3, "b": {"a": 4}}}}})
