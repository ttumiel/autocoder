import functools
import traceback

from flask import Request, Response

from .functions import function_call

try:
    import functions_framework
except ImportError:
    print("Have you installed the `deploy` module requirements? `pip install chat2func[deploy]`")


def request_handler(fn=None, allow_cors=True):
    if fn is None:
        return functools.partial(request_handler, allow_cors=allow_cors)

    @functools.wraps(fn)
    @functions_framework.http
    def thunk(request: Request):
        if allow_cors:
            # Set CORS headers for the preflight request
            if request.method == "OPTIONS":
                # Allows GET requests from any origin with the Content-Type
                # header and caches preflight response for an 3600s
                headers = {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "3600",
                }

                return ("", 204, headers)

            headers = {"Access-Control-Allow-Origin": "*"}
        else:
            headers = {}

        try:
            args = request.json if request.method == "POST" and request.is_json else {}
            result = function_call("fn", args, {"fn": fn}, validate=True, from_json=False)
            return Response(result, mimetype="application/json", headers=headers)
        except Exception as e:
            print(f"ERROR :: Function {fn.__name__} failed:\n", traceback.format_exc())
            return (f"Function call error: {e}", 400, headers)

    return thunk
