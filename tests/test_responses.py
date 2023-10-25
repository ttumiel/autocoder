from chat2func.schema import parse_function_responses


def test_no_annotation_no_doc():
    def func():
        pass

    assert parse_function_responses(func) == None


def test_with_annotation_no_doc():
    def func() -> list:
        pass

    expected = {
        "200": {
            "description": "OK",
            "content": {"application/json": {"schema": {"items": {}, "type": "array"}}},
        }
    }
    assert parse_function_responses(func) == expected


def test_no_annotation_with_doc():
    def func():
        """Desc
        Returns:
            list: A list of items.
        """
        pass

    expected = {
        "200": {
            "description": "A list of items.",
            "content": {"application/json": {"schema": {"items": {}, "type": "array"}}},
        }
    }
    assert parse_function_responses(func) == expected


def test_with_annotation_with_doc():
    def func() -> int:
        """Desc

        Returns:
            values
        """
        pass

    expected = {
        "200": {
            "description": "values",
            "content": {"application/json": {"schema": {"type": "integer"}}},
        }
    }
    assert parse_function_responses(func) == expected


def test_descriptions_false():
    def func() -> int:
        """Desc

        Returns:
            int: value
        """
        pass

    expected = {
        "200": {
            "description": "OK",
            "content": {"application/json": {"schema": {"type": "integer"}}},
        }
    }
    assert parse_function_responses(func, descriptions=False) == expected


def test_eval_exception():
    def func():
        """Desc

        Returns:
            UnknownType: An unknown type.
        """
        pass

    expected = {"200": {"description": "An unknown type."}}
    assert parse_function_responses(func) == expected
