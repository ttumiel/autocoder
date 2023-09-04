## Autocoder

### Overview

`autocoder` automatically generates JSON schemas from Python functions, classes, and data structures to be called with the OpenAI function calling API.

### Installation

```bash
# Clone the repo
git clone git@github.com:ttumiel/autocoder.git
cd autocoder
pip install -e .
```

### Quick Start

#### Annotate your function with `@json_schema`

```python
from autocoder import json_schema

@json_schema
def my_function(arg1: int, arg2: str) -> bool:
    """This is a sample function."""
    return arg1 == int(arg2)
```

After this, `my_function` will have an additional `.json` attribute containing its JSON schema.

```python
print(my_function.json)

{'description': 'This is a sample function.',
 'name': 'my_function',
 'parameters': {'properties': {'arg1': {'type': 'integer'},
                               'arg2': {'type': 'string'}},
                'required': ['arg1', 'arg2'],
                'type': 'object'}}
```

#### Using Custom Classes

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
