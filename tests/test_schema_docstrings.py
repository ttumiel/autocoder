import pytest

from chat2func import json_schema


@pytest.mark.parametrize(
    "docstring",
    [
        """desc

    :param arg1: a1
    :type arg1: int
    :param arg2: a2
    :type arg2: str
    :param arg3: a3
    :type arg3: float, optional
    :return: r1
    :rtype: bool
    """,
        """
    desc

    Args:
        arg1 (int): a1
        arg2 (str): a2
        arg3 (float, optional): a3

    Returns:
        bool: r1
    """,
        """
    desc

    Parameters
    ----------
    arg1 : int
        a1
    arg2 : str
        a2
    arg3 : float, optional
        a3

    Returns
    -------
    bool
        r1
    """,
    ],
)
def test_rest_doc(docstring):
    def example_function(arg1: int, arg2: str, arg3: float = 0.0) -> bool:
        pass

    example_function.__doc__ = docstring

    assert json_schema(example_function).json == {
        "name": "example_function",
        "description": "desc",
        "parameters": {
            "type": "object",
            "required": ["arg1", "arg2"],
            "properties": {
                "arg1": {"type": "integer", "description": "a1"},
                "arg2": {"type": "string", "description": "a2"},
                "arg3": {"type": "number", "description": "a3", "default": 0.0},
            },
        },
        "responses": {
            "200": {
                "description": "r1",
                "content": {"application/json": {"schema": {"type": "boolean"}}},
            }
        },
    }
