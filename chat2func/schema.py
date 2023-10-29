"""Generating JSON schema for functions and classes"""

import inspect
import logging
from collections import OrderedDict
from dataclasses import dataclass, field, is_dataclass
from enum import Enum
from functools import partial, update_wrapper
from typing import Any, Callable, Dict, ForwardRef, Optional, Tuple, Union, get_args, get_origin

from docstring_parser import Docstring, parse
from pydantic import GetCoreSchemaHandler, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema, core_schema

logger = logging.getLogger(__name__)


@dataclass
class Parameter:
    name: str
    description: Optional[str] = None
    default: Optional[Any] = field(default_factory=lambda: inspect._empty)
    annotation: Optional[type] = field(default_factory=lambda: inspect._empty)


class SchemaGenerator(GenerateJsonSchema):
    def field_title_should_be_set(self, schema) -> bool:
        return False


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

    try:
        if is_dataclass(py_type):
            return parse_function_params(py_type)

        schema = TypeAdapter(py_type).json_schema(schema_generator=SchemaGenerator)
        schema.pop("title", None)
        return schema
    except Exception as e:
        if not isbuiltin(py_type) and (inspect.isclass(py_type) or inspect.isfunction(py_type)):
            return parse_function_params(py_type)
        raise e


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
        default = sig_param.default
        if default is inspect._empty:
            if "required" not in schema:
                schema["required"] = []
            schema["required"].append(name)

        # Include the description
        if descriptions and doc_param.description:
            desc = doc_param.description
            schema["properties"][name]["description"] = desc

        if default is not inspect._empty and annotation is not inspect._empty:
            if isinstance(default, annotation):
                if isinstance(default, Enum):
                    default = default.value
                schema["properties"][name]["default"] = default
            else:
                logger.warning(
                    f"Default value `{default}` does not match annotation `{annotation} in {function.__name__}`"
                )

    return schema


def parse_function_responses(function: Callable, descriptions: bool = True) -> Optional[dict]:
    "Generate a json schema of a function's responses."
    signature = inspect.signature(function)
    returns = parse(inspect.getdoc(function)).returns

    return_type = signature.return_annotation
    if return_type is inspect._empty:
        return_type = getattr(returns, "type_name", None)
        if return_type is None:
            return_type = inspect._empty

    if inspect.isclass(function):
        return_type = inspect._empty

    try:
        return_schema = type_to_schema(return_type)
    except:
        logger.error(f"Failed to generate return schema for {function.__name__}", exc_info=True)
        return_schema = None

    description = getattr(returns, "description", None)
    response = {}
    if return_schema:
        response["content"] = {"application/json": {"schema": return_schema}}

    # If there's a schema we need at least a minimal description of OK
    # Otherwise avoid a description if `descriptions=False`
    if (description and descriptions) or return_schema:
        if not descriptions:
            description = "OK"
        response["description"] = description or "OK"

    if response:
        return {"200": response}


class JsonSchema:
    def __init__(
        self,
        function: Callable = None,
        *,
        descriptions: bool = True,
        full_docstring: bool = False,
        responses_schema: bool = True,
        pydantic_schema: bool = True,
    ):
        "See `json_schema` entrypoint for docs."
        self._function = function
        self._descriptions = descriptions
        self._full_docstring = full_docstring
        self._responses_schema = responses_schema
        self._cached_schema = None
        self._name = getattr(function, "__name__", None)
        if self._name is None and hasattr(function, "__func__"):
            self._name = getattr(function.__func__, "__name__", None)

        if pydantic_schema:
            self._make_class_schema()

        update_wrapper(self, function)

    def __get__(self, obj, objtype=None):
        # bind function to instance, and rewrap with schema
        bound_method = self._function.__get__(obj, objtype)
        bound_schema = self.__class__(
            bound_method,
            descriptions=self._descriptions,
            full_docstring=self._full_docstring,
            responses_schema=self._responses_schema,
            pydantic_schema=False,
        )
        if obj is None:
            return bound_schema

        # cache method
        obj.__dict__[self._name] = bound_schema
        return obj.__dict__[self._name]

    def __call__(self, *args, **kwds):
        return self._function(*args, **kwds)

    def __getattr__(self, name):
        return getattr(self._function, name)

    @property
    def __schema__(self):
        if self._cached_schema is None:
            self._cached_schema = self._make_schema()
        return self._cached_schema

    def _make_schema(self):
        schema = {}
        schema["name"] = self._function.__name__
        schema["parameters"] = parse_function_params(self._function, self._descriptions)
        if self._responses_schema:
            responses = parse_function_responses(self._function, self._descriptions)
            if responses:
                schema["responses"] = responses
            else:
                logger.warning(
                    f"Failed to generate responses schema for {self._function.__name__}\n{responses}"
                )

        if self._descriptions:
            docstring = parse(inspect.getdoc(self._function))
            desc = docstring.short_description or ""

            if self._full_docstring and docstring.long_description:
                desc += "\n" + docstring.long_description

            if desc:
                schema["description"] = desc

        return schema

    def _make_class_schema(self):
        def __get_pydantic_core_schema__(
            source_type: Any, handler: GetCoreSchemaHandler
        ) -> CoreSchema:
            def _from_dict(value: Dict[str, Any]):
                return self._function(**value)

            from_dict_schema = core_schema.chain_schema(
                [
                    core_schema.dict_schema(),
                    core_schema.no_info_plain_validator_function(_from_dict),
                ]
            )

            return core_schema.json_or_python_schema(
                json_schema=from_dict_schema, python_schema=from_dict_schema
            )

        self.__get_pydantic_core_schema__ = __get_pydantic_core_schema__


def json_schema(
    function: Callable = None,
    *,
    descriptions: bool = True,
    full_docstring: bool = False,
    responses_schema: bool = True,
    pydantic_schema: bool = True,
):
    """Extracts the schema of a function into the `.__schema__` attribute.

    Args:
        function (Callable): The function to extract the schema from.
        descriptions (bool): Whether to include descriptions from the docstring
            in the schema. Defaults to True.
        full_docstring (bool): Whether to include the full docstring description,
            or just the short_description (first line). Defaults to False.
        responses_schema (bool): Whether to include the responses schema. Defaults to True.
        pydantic_schema (bool): Whether to include the pydantic core schema classmethod
            which allows pydantic instantiation of chat2func types. Defaults to True.

    Examples:
        ```
        @json_schema
        def test(a: int):
            "description"

        test.__schema__ == {
            "name": "test",
            "description": "description",
            "parameters": {"required": ["a"], "a": {"type": "int"}}
        }
        ```
    """
    assert not hasattr(function, "__schema__"), "Function already has a __schema__ attribute."
    assert (
        function is None or callable(function) or hasattr(function, "__get__")
    ), "`function` must be callable"

    if function is None:
        return partial(
            JsonSchema,
            descriptions=descriptions,
            full_docstring=full_docstring,
            responses_schema=responses_schema,
            pydantic_schema=pydantic_schema,
        )

    return JsonSchema(
        function,
        descriptions=descriptions,
        full_docstring=full_docstring,
        responses_schema=responses_schema,
        pydantic_schema=pydantic_schema,
    )


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

    if isinstance(function, JsonSchema):
        function = function._function

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

                try:  # First try to instantiate directly with pydantic
                    schema = TypeAdapter(ptype)
                    arguments[name] = schema.validate_python(arguments[name])

                except Exception as e:
                    # If that fails and it's a class/function, instantiate that
                    if inspect.isclass(ptype) or inspect.isfunction(ptype):
                        args, nested_kwargs = schema_to_type(ptype, arguments[name], scope, strict)
                        arguments[name] = ptype(*args, **nested_kwargs)

                    else:  # Otherwise try to instantiate basic types directly
                        try:
                            arguments[name] = instantiate_type(ptype, arguments[name], scope)
                        except Exception as e:
                            logger.error("TyperAdapter and instantiate_type failed", exc_info=True)
                            raise e

            except Exception as e:
                if strict:
                    raise e
                else:
                    logger.warning(f"Failed to instantiate {name} from ({arguments[name]}): {e}")

    bound_arguments = signature.bind(**arguments)
    bound_arguments.apply_defaults()
    return bound_arguments.args, bound_arguments.kwargs
