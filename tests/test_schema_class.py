import gc
from weakref import ref

import pytest

from chat2func import json_schema


class ClassSchema:
    def __init__(self, a: int = None, b: str = None):
        "init description"
        self.a = a
        self.b = b

    @json_schema
    def method(self, arg1: int, arg2: str):
        "method description"
        return arg1 == int(arg2)

    @json_schema
    @staticmethod
    def static(arg1: int, arg2: str):
        "static description"
        return arg1 == int(arg2)

    @json_schema
    @classmethod
    def classmethod(cls, arg1: int, arg2: str):
        "classmethod description"
        return cls(arg1, arg2)


@pytest.fixture
def class_schema():
    return ClassSchema(1, 2)


def test_class_schema_method(class_schema):
    assert class_schema.method(1, "1") is True
    assert class_schema.method.json == {
        "name": "method",
        "description": "method description",
        "parameters": {
            "type": "object",
            "required": ["arg1", "arg2"],
            "properties": {"arg1": {"type": "integer"}, "arg2": {"type": "string"}},
        },
    }


def test_class_schema_static(class_schema):
    assert class_schema.static(1, "1") is True
    assert class_schema.static.json == {
        "name": "static",
        "description": "static description",
        "parameters": {
            "type": "object",
            "required": ["arg1", "arg2"],
            "properties": {"arg1": {"type": "integer"}, "arg2": {"type": "string"}},
        },
    }

    assert ClassSchema.static(1, "1") is True
    assert ClassSchema.static.json == {
        "name": "static",
        "description": "static description",
        "parameters": {
            "type": "object",
            "required": ["arg1", "arg2"],
            "properties": {"arg1": {"type": "integer"}, "arg2": {"type": "string"}},
        },
    }


def test_class_schema_classmethod(class_schema):
    assert isinstance(class_schema.classmethod(1, "1"), ClassSchema)
    assert isinstance(ClassSchema.classmethod(1, "1"), ClassSchema)
    assert class_schema.classmethod.json == {
        "name": "classmethod",
        "description": "classmethod description",
        "parameters": {
            "type": "object",
            "required": ["arg1", "arg2"],
            "properties": {"arg1": {"type": "integer"}, "arg2": {"type": "string"}},
        },
    }


def test_garbage_collection():
    # Should I check disposal of the descriptor?
    class_schema = ClassSchema(1, 2)
    class_ref = ref(class_schema)

    assert class_ref() is not None

    del class_schema
    gc.collect()

    assert class_ref() is None
