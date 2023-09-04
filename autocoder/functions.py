import ast
import inspect
import json
import logging
import traceback
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import partial
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


def isbuiltin(py_type: type) -> bool:
    return getattr(py_type, "__module__", None) == "builtins"


def type_to_schema(py_type: type) -> Dict[str, str]:
    "Convert python types to json schemas."
    if py_type is inspect._empty:
        return {}

    if inspect.isclass(py_type) and issubclass(py_type, BaseModel):
        return py_type.model_json_schema()

    if not isbuiltin(py_type) and (inspect.isclass(py_type) or inspect.isfunction(py_type)):
        return parse_function_params(py_type)

    return TypeAdapter(py_type).json_schema()


def parse_function_params(function: Callable, descriptions: bool = True) -> dict:
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
        if descriptions and doc_param.description:
            schema["properties"][name]["description"] = doc_param.description

    return schema


def json_schema(function: Callable = None, *, descriptions: bool = True):
    """Extracts the schema of a function into the .json attribute.

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
    if function == None:
        return partial(json_schema, descriptions=descriptions)

    schema = {}
    schema["name"] = function.__name__

    docstring = parse(inspect.getdoc(function))
    desc = docstring.long_description or docstring.short_description
    if desc and descriptions:
        schema["description"] = desc

    schema["parameters"] = parse_function_params(function, descriptions)

    function.json = schema
    return function


def schema_to_type(function: Callable, arguments: Dict[str, Any]) -> (list, dict):
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


def function_call(
    name: str,
    arguments: str,
    variables: Optional[Dict[str, Callable]] = None,
    validate: bool = True,
):
    """Calls a function by name with a dictionary of arguments.

    Examples:
        ```
        def test(a: int) -> bool:
            return a > 0

        function_call("test", {"a": 1}) == True
        ```

    Raises:
        FunctionCallError: If the function call fails.
    """
    global_vars = variables or globals()
    if name not in global_vars:
        raise FunctionCallError(f"Function {name} not found.")

    function = global_vars[name]

    if validate:
        function = validate_call(function)

    try:
        arguments = json.loads(arguments)
    except:
        raise FunctionCallError("Arguments are not valid JSON.")

    try:
        args, kwargs = schema_to_type(function, arguments)
    except:
        raise FunctionCallError("Arguments do not match function signature.")

    try:
        result = function(*args, **kwargs)
    except Exception as e:
        logging.error(traceback.format_exc())  # Move to contextmanager
        raise FunctionCallError("Function call failed: " + str(e))

    try:
        result = json.dumps(result)
    except:
        logging.warning("Function result is not JSON serializable.")
        result = {"result": str(result)}

    return result
