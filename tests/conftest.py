from functools import partial

import pytest

from chat2func import function_call


@pytest.fixture
def call_builder():
    def build(function, **kwargs):
        return partial(function_call, "test", functions={"test": function}, **kwargs)

    return build
