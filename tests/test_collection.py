from dataclasses import dataclass

from autocoder.functions import collect_functions


def test_collect_function():
    fn = lambda: None
    functions = collect_functions(locals())
    assert "fn" in functions
    assert len(functions) == 1


def test_ignore_function():
    fn = lambda: None
    functions = collect_functions(locals(), include_functions=False)
    assert "fn" not in functions
    assert len(functions) == 0


def test_collect_class():
    class Foo:
        pass

    functions = collect_functions(locals())
    assert "Foo" in functions
    assert len(functions) == 1


def test_ignore_class():
    class Foo:
        pass

    functions = collect_functions(locals(), include_classes=False)
    assert "Foo" not in functions
    assert len(functions) == 0


def test_collect_dataclass():
    @dataclass
    class Foo:
        pass

    functions = collect_functions(locals())
    assert "Foo" in functions
    assert len(functions) == 1


def test_ignore_dataclass():
    @dataclass
    class Foo:
        pass

    functions = collect_functions(locals(), include_dataclasses=False, include_classes=False)
    assert "Foo" not in functions
    assert len(functions) == 0


def test_collect_imported_function():
    from autocoder import json_schema

    functions = collect_functions(locals(), collect_imports=True)
    assert "json_schema" in functions
    assert len(functions) == 1


def test_ignore_imported_function():
    from autocoder import json_schema

    functions = collect_functions(locals(), collect_imports=False)
    assert "json_schema" not in functions
    assert len(functions) == 0


def test_ignore_blacklisted_function():
    fn = lambda: None
    functions = collect_functions(locals(), blacklist=["fn"])
    assert "fn" not in functions
    assert len(functions) == 0


def test_collect_whitelisted_function():
    fn = lambda: None
    functions = collect_functions(locals(), include_functions=False, whitelist=["fn"])
    assert "fn" in functions
    assert len(functions) == 1


def test_add_schema():
    def fn():
        pass

    functions = collect_functions(locals(), add_schema=True)
    assert "fn" in functions
    assert len(functions) == 1
    assert hasattr(functions["fn"], "json")


@dataclass
class Foo:
    pass


def foo():
    pass


def test_global_collection():
    fn = lambda: None
    functions = collect_functions(globals())
    assert "Foo" in functions
    assert "foo" in functions
