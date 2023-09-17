# chat2func

[![CI](https://github.com/ttumiel/chat2func/actions/workflows/ci.yml/badge.svg)](https://github.com/ttumiel/chat2func/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/ttumiel/chat2func)](https://github.com/ttumiel/chat2func/blob/main/LICENSE.txt)


`chat2func` automatically generates JSON schemas from Python, allowing ChatGPT to talk to your code.

## Installation

```bash
# Clone the repo
git clone git@github.com:ttumiel/chat2func.git
cd chat2func
pip install -e .
```

## Quick Start

### Annotate your function with `@json_schema`

```python
from chat2func import json_schema

@json_schema
def my_function(x: float, y: float) -> bool:
    """This is a sample function.

    Args:
        x: The first float.
        y: Another float.
    """
    return x > y
```

After this, `my_function` will have an additional `.json` attribute containing its JSON schema.

```python
print(my_function.json)

{'description': 'This is a sample function.',
 'name': 'my_function',
 'parameters': {'properties': {'x': {'description': 'The first float.', 'type': 'number'},
                               'y': {'description': 'Another float.', 'type': 'number'}},
                'required': ['x', 'y'],
                'type': 'object'}}
```

### Using Custom Classes

`json_schema` works with classes or dataclasses too. Set `descriptions=False` to not generate object descriptions from docstrings.

```python
@json_schema(descriptions=False)
@dataclass
class Data:
    a: int = 0

print(Data.json)
{'name': 'Data',
 'parameters': {'type': 'object', 'properties': {'a': {'type': 'integer'}}}}
```

### Calling Functions with JSON Arguments

`function_call` provides additional functionality for calling functions with JSON arguments. It automatically converts JSON arguments to Python objects and returns the result as JSON. It validates the JSON, raising `FunctionCallError` if something is unexpected.

```python
import json
from chat2func import function_call, collect_functions

def plusplus(x: float, y: float) -> float:
    "Add two floats."
    return x + y

# Specify the available functions.
# You can also use `collect_functions` to collect all functions within a scope.
functions = {"plusplus": plusplus}

# Arguments are passed as a JSON string.
arguments = json.dumps({"x": 1.0, "y": 2.0})
result = function_call("plusplus", arguments, functions)
print(result) # 3.0

# We can optionally validate the function arguments too. Defaults to on.
arguments = json.dumps({"x": "a", "y": 2.0})
result = function_call("plusplus", arguments, functions)
# FunctionCallError: Function call failed. 1 validation error for plusplus
```

### Creating a ChatGPT Plugin

You can easily create and demo a ChatGPT plugin using the included server. First, install the additional server requirements using `pip install -e .[server]`. Then, define the functions you want ChatGPT to be able to use, expose them with the server and connect to them from ChatGPT. Visit http://localhost:3333/ to see the available functions.

```python
from chat2func.server import FunctionServer

def addition(x: float, y: float) -> float:
    "Add two floats."
    return x + y

server = FunctionServer({"addition": addition})
server.run()
```
