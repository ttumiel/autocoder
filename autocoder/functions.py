"""Generating JSON schema for functions and classes"""

import inspect
import json
import logging
import traceback
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field, is_dataclass
from functools import partial
from typing import Any, Callable, Dict, Optional, Set

from docstring_parser import Docstring, parse
from pydantic import BaseModel, TypeAdapter, validate_call

logger = logging.getLogger(__name__)


class FunctionCallError(Exception):
    pass


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
            desc = doc_param.description
            if "default" not in desc.lower() and sig_param.default is not inspect._empty:
                desc += " (default: {})".format(sig_param.default)
            schema["properties"][name]["description"] = desc

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
            "parameters": {"required": ["a"], "a": {"type": "int"}}
        }
        ```
    """
    assert not hasattr(function, "json"), "Function already has a json attribute."

    if function is None:
        return partial(json_schema, descriptions=descriptions)

    schema = {}
    schema["name"] = function.__name__
    schema["parameters"] = parse_function_params(function, descriptions)

    if descriptions:
        docstring = parse(inspect.getdoc(function))
        desc = docstring.long_description or docstring.short_description
        if desc:
            schema["description"] = desc

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


@contextmanager
def function_call_error(error: str):
    try:
        yield
    except Exception as e:
        exc = traceback.format_exc()
        logger.error("Function Call Exception:\n" + exc)
        if error:
            raise FunctionCallError(error + f" {e}")


def function_call(
    name: str,
    arguments: str,
    functions: Dict[str, Callable],
    validate: bool = True,
    from_json: bool = True,
    return_json: bool = True,
) -> str:
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
    with function_call_error(f"Function {name} not found."):
        function = functions[name]

    if validate:
        function = validate_call(function)

    if from_json:
        with function_call_error("Arguments are not valid JSON."):
            arguments = json.loads(arguments)

    with function_call_error("Arguments do not match function signature."):
        args, kwargs = schema_to_type(function, arguments)

    with function_call_error("Function call failed."):
        result = function(*args, **kwargs)

    if return_json:
        try:
            result = json.dumps(result)
        except:
            logger.warning("Function result is not JSON serializable.")
            result = json.dumps({"result": str(result)})

    return result


def collect_functions(
    scope: Optional[Dict[str, Any]] = None,
    include_functions: bool = True,
    include_classes: bool = True,
    include_dataclasses: bool = True,
    collect_imports: bool = False,
    whitelist: Optional[Set[str]] = None,
    blacklist: Optional[Set[str]] = None,
    add_schema: bool = False,
):
    """
    Collects functions, classes, and dataclasses from a given scope.

    Args:
        scope (dict): The scope within which to collect functions, classes, etc. Defaults to None.
        include_functions (bool, optional): Whether to include functions. Defaults to True.
        include_classes (bool, optional): Whether to include classes. Defaults to True.
        include_dataclasses (bool, optional): Whether to include dataclasses. Defaults to True.
        collect_imports (bool, optional): Whether to include imported functions/classes. Defaults to False.
        whitelist (set, optional): Set of names to explicitly include. Defaults to None.
        blacklist (set, optional): Set of names to explicitly exclude. Defaults to None.
        add_schema (bool, optional): Whether to add a JSON schema for each collected item. Defaults to False.

    Returns:
        dict: A dictionary containing the collected functions, classes, and/or dataclasses.

    Examples:
        >>> fn = lambda: None
        >>> collect_functions()
        {'fn': <function <lambda> at 0x7f2bfa163d90>}
    """
    functions = {}
    last_globals = inspect.currentframe().f_back.f_globals
    scope = scope or last_globals
    scope_name = scope.get("__name__", last_globals["__name__"])
    for name, fn in scope.items():
        if blacklist and name in blacklist:
            continue

        if whitelist and name in whitelist:
            functions[name] = fn
            continue

        if isbuiltin(fn):
            continue

        if not collect_imports and getattr(fn, "__module__", None) != scope_name:
            continue

        if include_functions and inspect.isfunction(fn):
            functions[name] = fn
        elif include_classes and inspect.isclass(fn):
            functions[name] = fn
        elif include_dataclasses and is_dataclass(fn):
            functions[name] = fn

    if add_schema:
        functions = {name: json_schema(f) for name, f in functions.items()}

    return functions
