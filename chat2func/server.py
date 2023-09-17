"Local server for testing plugins"

import inspect
import json
import os
from functools import wraps
from pathlib import Path
from typing import Callable, Dict

from .functions import function_call, json_schema

try:
    import yaml
    from flask import Flask, Response, jsonify, render_template_string, request, send_file
    from flask_cors import CORS
except ImportError:
    print("Have you installed the server module requirements? `pip install chat2func[server]`")


class FunctionServer:
    def __init__(self, functions: Dict[str, Callable], port: int = 3333, validate: bool = True):
        self.port = port
        self.validate = validate
        self.functions = {}
        self.schemas = {}
        self.app = Flask(__name__, static_folder=None)

        CORS(self.app, origins=[f"http://localhost:{port}", "https://chat.openai.com"])

        for route, func in functions.items():
            self.create_route(route, func, self.validate)

        self.plugin_routes()

    def create_route(self, route, func, validate=True):
        schema = getattr(func, "json", None) or json_schema(func).json
        self.functions[route] = func
        self.schemas[route] = schema

        @self.app.route("/" + route, methods=["GET", "POST"])
        @wraps(func)
        def wrapper():
            try:
                args = request.json if request.method == "POST" and request.is_json else {}
                result = function_call(
                    route, args, self.functions, validate=validate, from_json=False
                )
                return Response(result, mimetype="application/json")

            except Exception as e:
                return jsonify({"Error": str(e)}), 400

    def plugin_routes(self):
        @self.app.route("/logo.png")
        def plugin_logo():
            current_dir = os.path.dirname(__file__)
            image_path = os.path.join(current_dir, "..", "logo.png")
            return send_file(image_path, mimetype="image/png")

        self.plugin_json = build_plugin_json(self.port)

        @self.app.route("/.well-known/ai-plugin.json")
        def plugin_manifest():
            return Response(json.dumps(self.plugin_json), mimetype="application/json")

        self.openapi_schema = build_openapi_spec(self.schemas)

        @self.app.route("/openapi.yaml")
        def openapi_spec():
            return Response(yaml.dump(self.openapi_schema), mimetype="text/yaml")

        @self.app.route("/")
        def index():
            routes = [(rule.endpoint, rule.rule) for rule in self.app.url_map.iter_rules()]
            return render_template_string(
                """
                <h1>Available Routes:</h1>
                <ul>
                {% for endpoint, route in routes %}
                    <li><b>{{ endpoint }}:</b> <a href="{{ route }}">{{ route }}</a></li>
                {% endfor %}
                </ul>
            """,
                routes=routes,
            )

    def run(self, debug=True, **kwargs):
        self.app.run(debug=debug, port=self.port, **kwargs)

    def export(self, path: str):
        """Dump the plugin files into a new dir, ready for deployment.
        This is experimental. You should confirm that all necessary imports
        and additional code files are added.
        """
        from .deploy import request_handler

        path = Path(path)
        path.mkdir(exist_ok=True, parents=True)
        with open(path / "requirements.txt", "a") as f:
            f.write("functions-framework==3.*\n")
            f.write("git+https://github.com/ttumiel/chat2func.git # chat2func\n")
            f.write("# Append all project requirements here:\n")

        with open(path / "main.py", "w") as f:
            f.write(
                "import functools\nimport traceback\n\nfrom chat2func import function_call\nimport functions_framework\nfrom flask import Request, Response\n\n\n"
            )
            f.write(inspect.getsource(request_handler) + "\n\n")

            for function in self.functions.values():
                f.write("@request_handler\n" + inspect.getsource(function) + "\n\n")

        well_known = path / ".well-known"
        well_known.mkdir(exist_ok=True)
        with open(well_known / "ai-plugin.json", "w") as f:
            f.write(json.dumps(self.plugin_json, indent=4))

        with open(path / "openapi.yaml", "w") as f:
            f.write(yaml.dump(self.openapi_schema))


def build_plugin_json(port: int) -> dict:
    "Builds an example dict of a plugin's `ai-plugin.json` file."
    return {
        "schema_version": "v1",
        "name_for_human": "Example Plugin",
        "name_for_model": "testing_plugin",
        "description_for_human": "Example plugin.",
        "description_for_model": "I'm testing my new plugin. Please point out anything that isn't right or that goes wrong with as much detail as possible.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": f"http://localhost:{port}/openapi.yaml"},
        "logo_url": f"http://localhost:{port}/logo.png",
        "contact_email": "legal@example.com",
        "legal_info_url": "http://example.com/legal",
    }


def build_openapi_spec(schemas: Dict[str, dict]) -> dict:
    "Builds the OpenAPI spec from a set of function schemas."
    paths = {}
    for func_name, schema in schemas.items():
        paths[f"/{func_name}"] = {
            "post": {
                "operationId": func_name,
                "summary": schema.get("description", f"{func_name} function"),
                "parameters": [],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": schema["parameters"]}},
                },
                "responses": {"200": {"description": "OK"}},
            }
        }

    openapi_spec = {
        "openapi": "3.0.1",
        "info": {
            "title": "Testing Plugin",
            "description": "Testing a ChatGPT plugin with these functions: "
            + ", ".join(schemas.keys()),
            "version": "v1",
        },
        "paths": paths,
    }

    return openapi_spec
