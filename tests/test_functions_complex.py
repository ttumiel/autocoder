from dataclasses import dataclass
from functools import partial

import pytest

from chat2func import function_call


@dataclass
class A:
    a: int
    b: bool = False


@dataclass
class B:
    a: A
    b: int


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


def test_nested_function_call(test_function):
    call = partial(
        function_call, "test", functions={"test": test_function}, return_json=False, from_json=False
    )
    assert call({"a": {"a": 1, "b": True}, "b": {"a": {"a": 2, "b": False}, "b": 3}, "c": 4})
