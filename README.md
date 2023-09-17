# chat2func

[![CI](https://github.com/ttumiel/chat2func/actions/workflows/ci.yml/badge.svg)](https://github.com/ttumiel/chat2func/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/ttumiel/chat2func)](https://github.com/ttumiel/chat2func/blob/main/LICENSE.txt)
[![PyPI](https://img.shields.io/pypi/v/chat2func.svg)](https://pypi.org/project/chat2func/)


`chat2func` automatically generates JSON schemas from Python, allowing ChatGPT to talk to your code.

## Installation

```bash
pip install chat2func
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

## JSON Schema

You can generate a JSON schema from any type of callable: classes, functions, or dataclasses.

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


## Creating a ChatGPT Plugin

You can easily create and demo a ChatGPT plugin using the included Flask server. First, install the additional server requirements using `pip install chat2func[server]`. Then, define the functions you want ChatGPT to be able to use, expose them with the server and connect to them from ChatGPT.

```python
from chat2func.server import FunctionServer

def addition(x: float, y: float) -> float:
    "Add two floats."
    return x + y

server = FunctionServer({"addition": addition})
server.run() # Visit http://localhost:3333/ to see the available functions.
```


### Deploy a Plugin

The `PluginServer` is a simple Flask app, so you can deploy easily using any method that works for Flask. The server provides an additional `export` function that generates the necessary files to deploy a plugin using firebase.

```python
# ...
server.export("./my-plugin")
```

After export, double check that all necessary code and imports are inside `main.py`. Also add a logo to `/public`.

```bash
cd my-plugin
python3.11 -m venv functions/venv && source functions/venv/bin/activate
pip install -r functions/requirements.txt
firebase emulators:start # test the function locally
firebase deploy # deploy to firebase
```

Don't forget to update the urls in `ai-plugin.json` once you've deployed.


## Calling Functions with JSON Arguments

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

### Using OpenAI's Function Calling API

**experimental**

We can use the function calling API directly too. Here we demonstrate using ChatGPT to generate structured data (in the form of dataclasses) from unstructured knowledge about the book _Dune_.

```python
from chat2func import function_call
from chat2func.api import FunctionCallingAPI, Role

@json_schema
@dataclass
class Character:
    name: str
    age: Optional[int] = None
    house: Optional[str] = None

# Setup our function calling API
api = FunctionCallingAPI({"Character": Character})
api.chat.add_message(Role.USER.value, "List the heads of houses in the Dune series. Give best estimates of age's where appropriate.")

# Generate 5 different Characters (remember the samples are stochastic!)
for _ in range(5):
    # Force the API to call a function
    message = api.reply(force_function="Character")
    api.chat.messages.append(message)

    # Call the function (and validate the inputs!)
    fn_name = message.function_call["name"]
    args = message.function_call["arguments"]
    result = function_call(fn_name, args, functions, return_json=False)

    # Add the result to the chat
    api.chat.add_message(Role.FUNCTION.value, str(result), name="character")
    print(result)

# Character(name='Duke Leto Atreides', age=50, house='Atreides')
# Character(name='Baron Vladimir Harkonnen', age=80, house='Harkonnen')
# Character(name='Emperor Shaddam Corrino IV', age=70, house='Corrino')
# Character(name='Lady Jessica', age=36, house='Atreides')
# Character(name='Paul Atreides', age=15, house='Atreides')
```
