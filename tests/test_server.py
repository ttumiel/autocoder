import json
from dataclasses import dataclass

from autocoder.server import FunctionServer


def fn_route_exists(url_map, route: str):
    for rule in url_map.iter_rules():
        if rule.rule == "/" + route:
            return True
    return False


def make_client(functions):
    server = FunctionServer(functions)
    server.app.config["TESTING"] = True
    client = server.app.test_client()

    assert fn_route_exists(server.app.url_map, ".well-known/ai-plugin.json")
    assert fn_route_exists(server.app.url_map, "openapi.yaml")

    for fn_name in functions:
        assert fn_route_exists(server.app.url_map, fn_name)

    return client


@dataclass
class DataTest:
    "Create test objects."
    a: int
    b: float


def test_server_no_args():
    def foo():
        return True

    def bar(a: bool = False):
        "Test function."
        return True

    client = make_client({"foo": foo, "bar": bar})

    rv = client.get("/foo")
    assert rv.status_code == 200
    assert json.loads(rv.data)

    rv = client.get("/bar")
    assert rv.status_code == 200
    assert json.loads(rv.data)


def test_server_dataclass():
    client = make_client({"DataTest": DataTest})

    rv = client.post("/DataTest", json={"a": 1, "b": 2.0})
    assert rv.status_code == 200
    assert json.loads(rv.data) == {"result": "DataTest(a=1, b=2.0)"}


def test_server_with_args():
    def foo(a: int, b: float):
        "Create test objects."
        return True

    def bar(b: bool, c: str):
        "Create test objects."
        return True

    client = make_client({"foo": foo, "bar": bar})

    rv = client.post("/foo", json={"a": 1, "b": 2.0})
    assert rv.status_code == 200
    assert json.loads(rv.data)

    rv = client.post("/foo", json={"a": False, "b": "test"})
    assert rv.status_code == 400
    assert "Error" in json.loads(rv.data)

    rv = client.post("/bar", json={"b": False, "c": "test"})
    assert rv.status_code == 200
    assert json.loads(rv.data)

    rv = client.post("/bar", json={"a": 1, "b": 2.0})
    assert rv.status_code == 400
    assert "Error" in json.loads(rv.data)
