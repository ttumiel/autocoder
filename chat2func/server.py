"Local server for testing plugins"

import inspect
import json
import os
from functools import wraps
from pathlib import Path
from typing import Callable, Dict

from .functions import function_calls, json_schema

try:
    import yaml
    from flask import Flask, Response, jsonify, render_template_string, request, send_file
    from flask_cors import CORS
except ImportError:
    print("Have you installed the developer requirements? `pip install chat2func[develop]`")


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
        schema = getattr(func, "__schema__", None) or json_schema(func).__schema__
        self.functions[route] = func
        self.schemas[route] = schema

        @self.app.route("/" + route, methods=["GET", "POST"])
        @wraps(func)
        def wrapper():
            try:
                args = request.json if request.method == "POST" and request.is_json else {}
                result = function_calls(
                    route, self.functions, args, validate=validate, from_json=False
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

    def export(self, path: str, export_source: bool = True, alias: str = "def"):
        """Dump the plugin files into a new dir, ready for deployment to firebase.

        This is experimental. You should confirm that all necessary imports
        and additional code files are added. Also remember to add a logo and
        update the generated ai-plugin.json file to describe your new plugin
        and change the host URL.

        Args:
            path (str): Path to the directory to export to.
            export_source (bool): Whether to export the source code
                for the functions into `functions/main.py`. Defaults to True.
            alias (str): The alias suffix to use for imported functions.
        """
        from .deploy import (
            DEPLOY_IMPORTS,
            FIREBASE_CONFIG,
            FUNCTION_DEF,
            generate_imports_and_sources,
            request_handler,
        )

        path = Path(path)
        path.mkdir(exist_ok=True, parents=True)

        public = path / "public"
        public.mkdir(exist_ok=True)

        functions = path / "functions"
        functions.mkdir(exist_ok=True)

        with open(functions / "requirements.txt", "a") as f:
            f.write("firebase-functions\n")
            f.write("chat2func\n")
            f.write("# Append all other project requirements here:\n")

        if export_source:
            fn_imports, inline_functions = generate_imports_and_sources(
                self.functions.values(), alias
            )
            with open(functions / "main.py", "w") as f:
                f.write(DEPLOY_IMPORTS.format(imports=fn_imports))
                f.write(inspect.getsource(request_handler) + "\n\n")

                for name, function in self.functions.items():
                    if name in inline_functions:
                        f.write("@request_handler\n" + inspect.getsource(function) + "\n\n")
                    else:
                        f.write(FUNCTION_DEF.format(function=name, alias=alias))

        well_known = public / ".well-known"
        well_known.mkdir(exist_ok=True)
        with open(well_known / "ai-plugin.json", "w") as f:
            f.write(json.dumps(self.plugin_json, indent=4))

        with open(public / "openapi.yaml", "w") as f:
            f.write(yaml.dump(self.openapi_schema))

        with open(path / "firebase.json", "w") as f:
            config = FIREBASE_CONFIG.copy()
            config["hosting"]["rewrites"] = [
                {"source": "/" + fn, "function": fn} for fn in self.functions
            ]
            f.write(json.dumps(config, indent=4))

        with open(path / ".gitignore", "w") as f:
            f.write("logs\n*.log*\n.firebase/\n.env\n__pycache__\nvenv")

        print(f"Plugin exported to `{path}`")
        print(f"Run `cd {path} && firebase deploy` to publish.")


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
                "responses": schema.get("responses", {"200": {"description": "OK"}}),
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
