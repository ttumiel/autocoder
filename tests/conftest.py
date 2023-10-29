from functools import partial

import pytest

from chat2func import function_calls, json_schema


@pytest.fixture(params=(json_schema, lambda x: x))
def call_builder(request):
    def build(function, **kwargs):
        return partial(request.param(function_calls), "test", {"test": function}, **kwargs)

    return build
