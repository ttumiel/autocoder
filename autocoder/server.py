"Local server for testing plugins"

import json
from functools import wraps
from typing import Callable, Dict

import yaml
from flask import Flask, Response, jsonify, render_template_string, request
from flask_cors import CORS

from .functions import function_call, json_schema


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
                args = request.json if request.method == "POST" and request.is_json else "{}"
                result = function_call(route, args, self.functions, validate=validate)
                return Response(result, mimetype="application/json")

            except Exception as e:
                return jsonify({"Error": str(e)}), 400

    def plugin_routes(self):
        @self.app.route("/logo.png")
        def plugin_logo():
            red_pixel_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
            return Response(red_pixel_data, mimetype="image/png")

        self.plugin_json = self.build_plugin_json()

        @self.app.route("/.well-known/ai-plugin.json")
        def plugin_manifest():
            return Response(json.dumps(self.plugin_json), mimetype="application/json")

        self.openai_spec = self.build_openapi_spec()

        @self.app.route("/openapi.yaml")
        def openapi_spec():
            return Response(yaml.dump(self.openai_spec), mimetype="text/yaml")

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

    def build_plugin_json(self):
        return {
            "schema_version": "v1",
            "name_for_human": "Example Plugin",
            "name_for_model": "testing_plugin",
            "description_for_human": "Example plugin.",
            "description_for_model": "I'm testing my new plugin. Please point out anything that isn't right or that goes wrong with as much detail as possible.",
            "auth": {"type": "none"},
            "api": {"type": "openapi", "url": f"http://localhost:{self.port}/openapi.yaml"},
            "logo_url": f"http://localhost:{self.port}/logo.png",
            "contact_email": "legal@example.com",
            "legal_info_url": "http://example.com/legal",
        }

    def build_openapi_spec(self):
        paths = {}
        for func_name, schema in self.schemas.items():
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
                + ", ".join(self.functions.keys()),
                "version": "v1",
            },
            "paths": paths,
        }

        return openapi_spec

    def run(self, debug=True):
        self.app.run(debug=debug, port=self.port)
