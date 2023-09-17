import functools
import traceback

from .functions import function_call

try:
    from firebase_functions import https_fn, options
except ImportError:
    print("Have you installed the `deploy` module requirements? `pip install chat2func[deploy]`")


DEPLOY_IMPORTS = '''"""
Deploy python functions as ChatGPT plugins using firebase.

NOTE: Make sure you check the generated code, add a logo.png to
`/public` and update the `ai-plugin.json` file.
"""

import functools
import traceback

from firebase_admin import initialize_app
from firebase_functions import https_fn, options

from chat2func import function_call

initialize_app()


'''

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
        cors=options.CorsOptions(cors_origins=[r"*"], cors_methods=["get", "post"])
    )
    @functools.wraps(fn)
    def thunk(request: https_fn.Request):
        try:
            args = request.json if request.method == "POST" and request.is_json else {}
            result = function_call("fn", args, {"fn": fn}, validate=True, from_json=False)
            return https_fn.Response(result, mimetype="application/json")
        except Exception as e:
            print(f"ERROR :: Function {fn.__name__} failed:\n", traceback.format_exc())
            return (f"Function call error: {e}", 400)

    return thunk
