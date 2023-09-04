import ast
import inspect
import json
import logging
import traceback
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from docstring_parser import Docstring, parse
from pydantic import BaseModel, TypeAdapter, validate_call

logger = logging.getLogger(__name__)


class FunctionCallError(Exception):
    pass


### Generating JSON schema for functions and dataclasses ###


@dataclass
class Parameter:
    name: str
    description: Optional[str] = None
    default: Optional[Any] = field(default_factory=lambda: inspect._empty)
    annotation: Optional[type] = field(default_factory=lambda: inspect._empty)


def docstring_to_params(docstring: Docstring) -> Dict[str, Parameter]:
    params = OrderedDict()
    for param in docstring.params:
        default = param.default if param.is_optional else inspect._empty
        try:
            annotation = eval(param.type_name)
        except:
            annotation = param.type_name
        params[param.arg_name] = Parameter(param.arg_name, param.description, default, annotation)
    return params


def isbuiltin(py_type) -> bool:
    return getattr(py_type, "__module__", None) == "builtins"


def type_to_schema(py_type) -> dict:
    "Convert python types to json schemas."
    if py_type is inspect._empty:
        return {}

    if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
        return py_type.model_json_schema()

    if not isbuiltin(py_type) and (inspect.isclass(py_type) or inspect.isfunction(py_type)):
        return parse_function_params(py_type)

    return TypeAdapter(py_type).json_schema()


def parse_function_params(function: Callable, use_param_descriptions=True) -> dict:
    "Generate a json schema of a function's parameters."
    schema = {}
    signature = inspect.signature(function)
    docstring = parse(inspect.getdoc(function))
    docstring_params = docstring_to_params(docstring)

    schema = {"type": "object", "properties": {}}
    for name, sig_param in signature.parameters.items():
        doc_param = docstring_params.get(name, Parameter(name))

        # Get the JSON type
        annotation = (
            sig_param.annotation
            if sig_param.annotation is not inspect._empty
            else doc_param.annotation
        )
        schema["properties"][name] = type_to_schema(annotation)

        # Check if required
        if sig_param.default is inspect._empty:
            if "required" not in schema:
                schema["required"] = []
            schema["required"].append(name)

        # Include the description
        if use_param_descriptions and doc_param.description:
            schema["properties"][name]["description"] = doc_param.description

    return schema


def schema_to_type(function, arguments) -> (list, dict):
    "Convert json objects to python function arguments."
    signature = inspect.signature(function)
    for name, parameter in signature.parameters.items():
        if name in arguments:
            if (
                not isbuiltin(parameter.annotation)
                and inspect.isclass(parameter.annotation)
                or inspect.isfunction(parameter.annotation)
            ):
                arguments[name] = parameter.annotation(**arguments[name])

    # TODO: recursive call for nested objects

    bound_arguments = signature.bind(**arguments)
    bound_arguments.apply_defaults()
    return bound_arguments.args, bound_arguments.kwargs


def json_schema(function=None, *, use_param_descriptions=True):
    """Extracts the schema of a function and adds a .json attribute.

    Examples:
        ```
        @json_schema
        def test(a: int) -> bool:
            "description"

        test.json == {
            "name": "test",
            "description": "description",
            "parameters": {
                "required": ["a"],
                "a": {
                    "type": "int",
                }
            }
        }
        ```
    """
    schema = {}
    schema["name"] = function.__name__

    docstring = parse(inspect.getdoc(function))
    desc = docstring.long_description or docstring.short_description
    if desc and use_param_descriptions:
        schema["description"] = desc

    schema["parameters"] = parse_function_params(function, use_param_descriptions)

    function.json = schema
    return function
