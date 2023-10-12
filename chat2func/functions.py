"""Generating JSON schema for functions and classes"""

import inspect
import json
import logging
import traceback
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field, is_dataclass
from functools import partial, update_wrapper
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    Optional,
    Set,
    Tuple,
    Union,
    get_args,
    get_origin,
)

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
    return getattr(py_type, "__module__", None) in ("builtins", "__builtin__")


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


class JsonSchema:
    def __init__(
        self, function: Callable = None, *, descriptions: bool = True, full_docstring: bool = False
    ):
        self.function = function
        self.descriptions = descriptions
        self.full_docstring = full_docstring
        self._cached_schema = None
        self.name = getattr(function, "__name__", None)
        if self.name is None and hasattr(function, "__func__"):
            self.name = getattr(function.__func__, "__name__", None)

        update_wrapper(self, function)

    def __get__(self, obj, objtype=None):
        # bind function to instance, and rewrap with schema
        bound_method = self.function.__get__(obj, objtype)
        bound_schema = self.__class__(bound_method, descriptions=self.descriptions)
        if obj is None:
            return bound_schema

        # cache method
        obj.__dict__[self.name] = bound_schema
        return obj.__dict__[self.name]

    def __call__(self, *args, **kwds):
        return self.function(*args, **kwds)

    @property
    def json(self):
        if self._cached_schema is None:
            self._cached_schema = self.make_schema()
        return self._cached_schema

    def make_schema(self):
        schema = {}
        schema["name"] = self.function.__name__
        schema["parameters"] = parse_function_params(self.function, self.descriptions)

        if self.descriptions:
            docstring = parse(inspect.getdoc(self.function))
            desc = docstring.short_description or ""

            if self.full_docstring and docstring.long_description:
                desc += "\n" + docstring.long_description

            if desc:
                schema["description"] = desc

        return schema


def json_schema(
    function: Callable = None, *, descriptions: bool = True, full_docstring: bool = False
):
    """Extracts the schema of a function into the .json attribute.

    Args:
        function (Callable): The function to extract the schema from.
        descriptions (bool): Whether to include descriptions from the docstring
            in the schema. Defaults to True.
        full_docstring (bool): Whether to include the full docstring description,
            or just the short_description (first line). Defaults to False.

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
    assert callable(function) or hasattr(function, "__get__"), "`function` must be callable"

    if function is None:
        return partial(JsonSchema, descriptions=descriptions, full_docstring=full_docstring)

    return JsonSchema(function, descriptions=descriptions, full_docstring=full_docstring)


def _get_outer_globals() -> Dict[str, Any]:
    "Attempts to get globals() from the calling module."
    frame = inspect.currentframe()

    while frame:
        module = inspect.getmodule(frame)
        if getattr(module, "__package__", None) != __package__:
            return frame.f_globals

        frame = frame.f_back
    return {}


def _evaluate_forward_ref(ref: ForwardRef, scope: Dict[str, Any]):
    if "recursive_guard" in inspect.signature(ForwardRef._evaluate).parameters:
        kwds = {"recursive_guard": frozenset()}
    else:
        kwds = {}
    return ref._evaluate(scope, None, **kwds)


def instantiate_type(py_type: type, value: Any, scope: Optional[Dict[str, Any]] = None) -> Any:
    """Instantiate a python type from a json value.

    Args:
        py_type (type): The python type to instantiate.
        value (Any): The value to instantiate the type with.
        scope (dict): The scope within which to evaluate the type. Defaults to the calling module.

    Raises:
        TypeError: Invalid value type for the given type.
        ValueError: If the type cannot be instantiated with the given value.
    """
    if py_type is inspect._empty or py_type is Any:
        return value

    if py_type is type(None) and value is None:
        return None

    scope = scope or _get_outer_globals()
    if isinstance(py_type, ForwardRef):
        py_type = _evaluate_forward_ref(py_type, scope)

    try:
        return py_type(value)
    except (ValueError, TypeError):
        logger.info("Type not directly instantiable", exc_info=True)

    origin = get_origin(py_type)
    if origin:
        args = get_args(py_type)

        if origin is Union:
            if any((isinstance(arg, type) and isinstance(value, arg)) for arg in args):
                return value

            for arg in args:
                try:
                    return instantiate_type(arg, value, scope)
                except:
                    pass
            raise ValueError(f"Cannot instantiate any Union type ({args}) with value {value}")

        if origin is list:
            return list(instantiate_type(args[0], v, scope) for v in value)

        if origin is tuple:
            if (len(args) == 2 and args[1] is ...) or len(args) == 1:
                args = [args[0]] * len(value)
            return tuple(instantiate_type(t, v, scope) for t, v in zip(args, value))

        if origin is dict:
            key_type, value_type = args
            return {
                instantiate_type(key_type, k, scope): instantiate_type(value_type, v, scope)
                for k, v in value.items()
            }

        if origin is set:
            return set(instantiate_type(args[0], v, scope) for v in value)

        return origin(value)

    if not isbuiltin(py_type) and (inspect.isclass(py_type) or inspect.isfunction(py_type)):
        args, kwds = schema_to_type(py_type, value)
        return py_type(*args, **kwds)

    raise ValueError("Couldn't instantiate type", py_type, value)


def schema_to_type(
    function: Callable,
    arguments: Dict[str, Any],
    scope: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Tuple[list, dict]:
    "Convert json objects to python function arguments."

    signature = inspect.signature(function)
    scope = scope or _get_outer_globals()
    for name, parameter in signature.parameters.items():
        if name in arguments:
            ptype = parameter.annotation

            if ptype is inspect._empty or ptype is Any:
                continue

            try:
                if isinstance(ptype, ForwardRef):
                    ptype = _evaluate_forward_ref(ptype, scope)

                if not isbuiltin(ptype) and (inspect.isclass(ptype) or inspect.isfunction(ptype)):
                    args, nested_kwargs = schema_to_type(ptype, arguments[name], scope, strict)
                    arguments[name] = ptype(*args, **nested_kwargs)
                else:
                    arguments[name] = instantiate_type(ptype, arguments[name], scope)

            except Exception as e:
                if strict:
                    raise e
                else:
                    logger.warning(f"Failed to instantiate {name} from ({arguments[name]}): {e}")

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
    arguments: Union[str, Any],
    functions: Dict[str, Callable],
    validate: bool = True,
    from_json: bool = True,
    return_json: bool = True,
    scope: Optional[Dict[str, Any]] = None,
) -> str:
    """Calls a function by name with a dictionary of arguments.

    Args:
        name (str): The name of the function to call. A key inside `functions` arg.
        arguments (str, Any): JSON string (or py object if from_json=False) of the arguments
            to pass to the function.
        functions (dict): A dictionary of available functions to call.
        validate (bool, optional): Whether to validate the function call arg types. Not
            possible for classes. Defaults to True.
        from_json (bool, optional): Whether to load the arguments from JSON. Defaults to True.
        return_json (bool, optional): Whether to return the result as JSON. Defaults to True.
        scope (dict): The scope within which to evaluate the function's args, in order to
            resolve type references. Defaults to the calling module.

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
        if isinstance(function, type):
            logger.error("Cannot validate class calls.")
        else:
            function = validate_call(function)

    if from_json:
        with function_call_error("Arguments are not valid JSON."):
            arguments = json.loads(arguments)

    with function_call_error("Arguments do not match function signature."):
        args, kwargs = schema_to_type(function, arguments, scope=scope)

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
        scope (dict): The scope within which to collect functions, classes, etc. Defaults to the currentframe globals().
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
    scope = scope or _get_outer_globals()
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
