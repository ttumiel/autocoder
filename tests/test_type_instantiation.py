from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import pytest

from chat2func.functions import instantiate_type


def test_instantiate_simple_type():
    # Test basic types
    assert instantiate_type(int, "1") == 1
    assert instantiate_type(float, "1.1") == 1.1
    assert instantiate_type(str, 1) == "1"
    assert instantiate_type(bool, "True") == True

    # Test NoneType
    assert instantiate_type(type(None), None) is None

    # Test Union and Optional types
    assert instantiate_type(Union[int, str], 1) == 1
    assert instantiate_type(Union[int, str], "a") == "a"
    assert instantiate_type(Optional[int], "1") == 1
    assert instantiate_type(Optional[int], None) is None

    # Test list and tuple
    assert instantiate_type(List[int], ["1", "2"]) == [1, 2]
    assert instantiate_type(List[str], [1, 2]) == ["1", "2"]
    assert instantiate_type(list, [1, 2]) == [1, 2]
    assert instantiate_type(tuple, [1, 2]) == (1, 2)
    assert instantiate_type(Tuple[int], [1, 2]) == (1, 2)

    # Test dict
    assert instantiate_type(Dict[str, int], {"a": "1", "b": "2"}) == {"a": 1, "b": 2}
    assert instantiate_type(Dict[int, int], {"1": "1", "2": "2"}) == {1: 1, 2: 2}
    assert instantiate_type(dict, {"1": "1", "2": "2"}) == {"1": "1", "2": "2"}

    # Test str
    assert instantiate_type(str, "test") == "test"

    # Test set
    assert instantiate_type(set, ["1", "2"]) == {"1", "2"}
    assert instantiate_type(Set[int], ["1", "2"]) == {1, 2}

    # Test Any
    assert instantiate_type(Any, "anything") == "anything"
    assert instantiate_type(Any, None) == None

    # Test invalid cases
    with pytest.raises(ValueError):
        instantiate_type(int, "not_an_int")

    with pytest.raises(ValueError):
        instantiate_type(float, "not_a_float")

    with pytest.raises(ValueError):
        instantiate_type(Union[int, float], "not_a_number")

    with pytest.raises(ValueError):
        instantiate_type(Optional[int], "a")

    with pytest.raises(ValueError):
        instantiate_type(type(None), "none")

    with pytest.raises(ValueError):
        instantiate_type(int, None)

    with pytest.raises(Exception):
        instantiate_type(Callable, "a")


def test_instantiate_complex_types():
    # Test nested Union and Optional types
    assert instantiate_type(Union[Optional[int], str], "1") == "1"
    assert instantiate_type(Union[Optional[int], str], 1) == 1
    assert instantiate_type(Union[Optional[int], str], None) is None
    assert instantiate_type(Union[Optional[int], str], "a") == "a"

    # Test nested list
    assert instantiate_type(List[List[int]], [["1", "2"], ["3", "4"]]) == [[1, 2], [3, 4]]
    assert instantiate_type(List[Union[int, str]], [1, "a"]) == [1, "a"]

    # Test nested dict
    assert instantiate_type(Dict[str, Dict[str, int]], {"a": {"b": "1"}, "c": {"d": "2"}}) == {
        "a": {"b": 1},
        "c": {"d": 2},
    }
    assert instantiate_type(Dict[str, Union[int, str]], {"a": "1", "b": "b"}) == {
        "a": "1",
        "b": "b",
    }

    # Test nested tuple
    assert instantiate_type(Tuple[int, Tuple[str, int]], ("1", ("a", "2"))) == (1, ("a", 2))

    # Test nested set
    assert instantiate_type(Dict[str, Set[int]], {"a": [1, 2], "b": [3, 4]}) == {
        "a": {1, 2},
        "b": {3, 4},
    }

    # Test combination of complex types
    assert instantiate_type(
        Dict[str, List[Union[int, Tuple[int, str]]]], {"a": ["1", ("2", "b")]}
    ) == {"a": [1, (2, "b")]}

    # Test invalid nested types
    with pytest.raises(ValueError):
        instantiate_type(List[List[int]], [["1", "a"], ["3", "4"]])

    with pytest.raises(ValueError):
        instantiate_type(Dict[str, Dict[str, int]], {"a": {"b": "c"}, "d": {"e": "2"}})

    with pytest.raises(ValueError):
        instantiate_type(Tuple[int, Tuple[str, int]], ("a", ("b", "2")))

    with pytest.raises(ValueError):
        instantiate_type(Set[Set[int]], [{1, "a"}, {3, 4}])

    with pytest.raises(ValueError):
        print(instantiate_type(Union[Optional[int], float], {"a": 3}))
