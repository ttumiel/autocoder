import inspect
import json
import logging
import traceback
from contextlib import contextmanager
from dataclasses import is_dataclass
from typing import Any, Callable, Dict, Optional, Set, Union

import jsonschema

from .schema import JsonSchema, _get_outer_globals, isbuiltin, json_schema, schema_to_type

logger = logging.getLogger(__name__)


class FunctionCallError(Exception):
    pass


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
    function: Callable,
    arguments: Union[str, Any],
    validate: bool = True,
    from_json: bool = True,
    return_json: bool = True,
    scope: Optional[Dict[str, Any]] = None,
) -> Union[str, Any]:
    """Calls a function with argument parsing and validation.

    Args:
        function (callable): The function to call.
        arguments (str, Any): JSON string (or py object if from_json=False) of the arguments
            to pass to the function.
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

        function_call(test, {"a": 1}) == True
        ```

    Raises:
        FunctionCallError: If the function call fails.

    Returns:
        Union[str, Any]: The result of the function call, as a JSON string if return_json=True.
    """
    if from_json:
        with function_call_error("Arguments are not valid JSON."):
            arguments = json.loads(arguments)

    if validate:
        with function_call_error("Arguments do not match the schema."):
            schema = (
                getattr(function, "__schema__", None)
                or JsonSchema(function, descriptions=False).__schema__
            )
            schema = schema["parameters"]
            jsonschema.validate(arguments, schema)

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


def function_calls(
    name: str,
    functions: Dict[str, Callable],
    arguments: Union[str, Any],
    validate: bool = True,
    from_json: bool = True,
    return_json: bool = True,
    scope: Optional[Dict[str, Any]] = None,
) -> Union[str, Any]:
    """Calls a function from a dict of available functions. To call a single function, use `function_call`.

    Args:
        name (str): The name of the function to call. A key inside `functions` arg.
        functions (dict): A dictionary of available functions to call.
        arguments (str, Any): JSON string (or py object if from_json=False) of the arguments
            to pass to the function.
        validate (bool, optional): Whether to validate the function call arg types. Not
            possible for classes. Defaults to True.
        from_json (bool, optional): Whether to load the arguments from JSON. Defaults to True.
        return_json (bool, optional): Whether to return the result as JSON. Defaults to True.
        scope (dict): The scope within which to evaluate the function's args, in order to
            resolve type references. Defaults to the calling module.

    Raises:
        FunctionCallError: If the function call fails.

    Returns:
        Union[str, Any]: The result of the function call, as a JSON string if return_json=True.
    """
    with function_call_error(f"Function `{name}` not found."):
        function = functions[name]

    return function_call(function, arguments, validate, from_json, return_json, scope)


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
