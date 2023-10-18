from functools import partial

import pytest

from chat2func import function_call, json_schema


@pytest.fixture(params=(json_schema, lambda x: x))
def call_builder(request):
    def build(function, **kwargs):
        return partial(request.param(function_call), "test", functions={"test": function}, **kwargs)

    return build
