import functools
import traceback
from collections import defaultdict
from typing import Callable, List, Optional, Set, Tuple

from .functions import function_call

try:
    from firebase_functions import https_fn, options
except ImportError:
    print("Have you installed the developer requirements? `pip install chat2func[develop]`")


DEPLOY_IMPORTS = '''"""
Deploy python functions as ChatGPT plugins using firebase.

NOTE: Make sure you check the generated code, add a logo.png to
`/public` and update the `ai-plugin.json` file.
"""

import functools
import traceback

from chat2func import function_call
from firebase_admin import initialize_app
from firebase_functions import https_fn, options

{imports}

initialize_app()


'''


FUNCTION_DEF = """
@request_handler
def {function}(*args, **kwargs):
    return {function}_def(*args, **kwargs)

"""


FIREBASE_CONFIG = {
    "functions": [
        {
            "source": "functions",
            "codebase": "default",
            "runtime": "python311",
            "ignore": ["venv", ".git", "*.log"],
        }
    ],
    "hosting": {
        "public": "public",
        "rewrites": [],
        "ignore": ["firebase.json", "**/.*"],
        "headers": [
            {
                "source": "**/*.@(json|yaml|yml)",
                "headers": [{"key": "Access-Control-Allow-Origin", "value": "*"}],
            }
        ],
    },
}


def request_handler(fn=None, allow_cors=True):
    if fn is None:
        return functools.partial(request_handler, allow_cors=allow_cors)

    @https_fn.on_request(
        cors=options.CorsOptions(cors_origins=[r"*"], cors_methods=["get", "post"]),
        memory=options.MemoryOption.MB_256,
        region=options.SupportedRegion.US_WEST1,
        cpu=1,
    )
    @functools.wraps(fn)
    def thunk(request: https_fn.Request):
        try:
            args = request.json if request.is_json else {}
            result = function_call(fn, args, validate=True, from_json=False)
            return https_fn.Response(result, mimetype="application/json")
        except Exception as e:
            print(f"ERROR :: Function {fn.__name__} failed:\n", traceback.format_exc())
            return (f"Function call error: {e}", 400)

    return thunk


def generate_imports_and_sources(
    func_list: List[Callable], alias: Optional[str] = None
) -> Tuple[str, Set[str]]:
    """Generate the imports and source code for the functions in `func_list`

    Args:
        func_list (List[Callable]): List of functions to generate code for.
        alias (Optional[str], optional): Alias to add to function imports. Defaults to None.
    """
    import_statements = defaultdict(set)
    inline_functions = set()

    for func in func_list:
        module_name = func.__module__
        func_name = func.__name__

        if module_name == "__main__":
            inline_functions.add(func_name)
        else:
            import_statements[module_name].add(func_name)

    import_strs = []
    for module, funcs in import_statements.items():
        fn_names = ", ".join((f"{fn} as {fn}_{alias}" if alias else fn) for fn in sorted(funcs))
        import_strs.append(f"from {module} import {fn_names}")

    all_imports = "\n".join(import_strs)

    return all_imports, inline_functions
