import json
from pathlib import Path

import yaml

from chat2func.server import FunctionServer


def test_export(tmp_path: Path):
    def addition(a: float, b: float):
        "Addition function"
        return a + b

    # Create a FunctionServer instance
    server = FunctionServer(functions={"addition": addition}, port=3333, validate=True)

    # Call the export method
    server.export(path=tmp_path, export_source=True, alias="def")

    # Check if directories are created
    assert (tmp_path / "public").exists()
    assert (tmp_path / "functions").exists()
    assert (tmp_path / "public" / ".well-known").exists()

    # Check if files are created
    assert (tmp_path / "functions" / "requirements.txt").exists()
    assert (tmp_path / "functions" / "main.py").exists()
    assert (tmp_path / "public" / ".well-known" / "ai-plugin.json").exists()
    assert (tmp_path / "public" / "openapi.yaml").exists()
    assert (tmp_path / "firebase.json").exists()
    assert (tmp_path / ".gitignore").exists()

    # Check the content of the files
    with open(tmp_path / "functions" / "requirements.txt", "r") as f:
        requirements = f.read()
        assert "firebase-functions" in requirements
        assert "chat2func" in requirements

    with open(tmp_path / "public" / ".well-known" / "ai-plugin.json", "r") as f:
        assert json.load(f) == server.plugin_json

    with open(tmp_path / "public" / "openapi.yaml", "r") as f:
        assert yaml.safe_load(f) == server.openapi_schema

    with open(tmp_path / "firebase.json", "r") as f:
        assert json.load(f)["hosting"]["rewrites"] == [
            {"source": "/" + fn, "function": fn} for fn in server.functions
        ]
