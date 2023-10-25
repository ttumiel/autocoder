import json
from math import cos, sin, tan

import pytest

from chat2func.deploy import generate_imports_and_sources
from chat2func.schema import json_schema


def my_function1():
    pass


def my_function2():
    return 1


@pytest.mark.parametrize(
    "func_list, expected_imports, expected_inlines",
    [
        ([sin, cos, my_function1], "from math import cos, sin", set(["my_function1"])),
        (
            [tan, json.dumps, my_function2],
            "from math import tan\nfrom json import dumps",
            set(["my_function2"]),
        ),
        ([my_function1, my_function2], "", set(["my_function1", "my_function2"])),
        ([sin, cos, tan], "from math import cos, sin, tan", set()),
        ([json_schema], "from chat2func.schema import json_schema", set()),
        ([], "", set()),
    ],
)
def test_generate_imports_and_sources(func_list, expected_imports, expected_inlines):
    my_function1.__module__ = "__main__"
    my_function2.__module__ = "__main__"

    imports, inlines = generate_imports_and_sources(func_list)
    assert imports == expected_imports
    assert inlines == expected_inlines


@pytest.mark.parametrize(
    "func_list, expected_imports, expected_inlines",
    [
        (
            [tan, json.dumps, my_function2],
            "from math import tan as tan_definition\nfrom json import dumps as dumps_definition",
            set(["my_function2"]),
        ),
        (
            [json_schema],
            "from chat2func.schema import json_schema as json_schema_definition",
            set(),
        ),
    ],
)
def test_generate_imports_and_sources_aliased(func_list, expected_imports, expected_inlines):
    my_function1.__module__ = "__main__"
    my_function2.__module__ = "__main__"
    alias = "definition"

    imports, inlines = generate_imports_and_sources(func_list, alias=alias)
    assert imports == expected_imports
    assert inlines == expected_inlines
