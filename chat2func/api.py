"Early version of the FunctionCallingAPI class. VERY experimental!"

import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from .functions import FunctionCallError, function_call, json_schema

try:
    from IPython.display import HTML, display

    IPYTHON = True
except ImportError:
    IPYTHON = False

try:
    import openai
    from tenacity import retry, stop_after_attempt, wait_random_exponential
except ImportError:
    print("Have you installed the API module requirements? `pip install chat2func[api]`")

SYSTEM_PROMPT = "You are a highly capable AI assistant, helping develop and test a function calling API. \
You can access the following functions and should use them when relevant: {functions}"


class ChatModel(Enum):
    GPT3_5 = "gpt-3.5-turbo"
    GPT4 = "gpt-4"


class Role(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class Message:
    role: str
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, str]] = None

    def as_dict(self):
        data = {"role": self.role, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.function_call:
            data["function_call"] = self.function_call
        return data


@dataclass
class Chat:
    functions: Optional[Dict[str, Callable]] = None
    messages: List[Message] = field(default_factory=list)

    def add_message(self, role: str, content: str, name: Optional[str] = None):
        msg = Message(role, content, name)
        self.messages.append(msg)

    @property
    def last_message(self):
        return self.messages[-1]

    def get_messages(self):
        return [m.as_dict() for m in self.messages]


class FunctionCallingAPI:
    def __init__(
        self,
        functions: Optional[Dict[str, Callable]] = None,
        sys_prompt: Optional[str] = None,
        model: str = ChatModel.GPT4.value,
    ):
        self.functions = functions or {}
        self.model = model
        self.schemas = [
            getattr(f, "json", None) or json_schema(f).json for name, f in functions.items()
        ]

        sys_prompt = (sys_prompt or SYSTEM_PROMPT).format(functions=", ".join(functions.keys()))
        self.chat = Chat(self.functions)
        self.chat.add_message(Role.SYSTEM.value, sys_prompt)

    def display(self, message: Message):
        """
        Display a chat message according to the role. Uses HTML for IPython and formatted text otherwise.
        """
        role_name = message.role.capitalize().ljust(12, " ")
        terminal_width = shutil.get_terminal_size().columns

        content = ""
        if message.name:
            content += message.name + ": "

        if message.content:
            content += message.content

        if message.function_call:
            if content:
                content += "\n"
            content += message.function_call

        if IPYTHON and "ipykernel" in sys.modules:
            block = f"""<div style="margin: 5px; padding: 5px;">
                            <pre><b>{role_name}</b>{content}</pre>
                        </div>
                        <hr/>"""
            display(HTML(block))
        else:
            message_width = terminal_width - len(role_name)
            print("-" * terminal_width)
            print(f"{role_name}{content[:message_width]}")
            for i in range(message_width, len(content), message_width):
                line = content[i : i + message_width]
                print(" " * len(role_name) + line)

    def run(self, continue_on_fn: bool = True):
        for message in self.chat.messages:
            self.display(message)

        while True:
            try:
                user_msg = input("")
                if user_msg == "quit" or user_msg == "exit":
                    break

                if user_msg:
                    self.chat.add_message(Role.USER.value, user_msg)

                self.reply()
                while continue_on_fn and self.chat.last_message["finish_reason"] == "function_call":
                    self.reply()
                    if self.chat.last_message["role"] == Role.ASSISTANT.value:
                        fn_name = self.chat.last_message["function_call"]["name"]
                        args = self.chat.last_message["function_call"]["arguments"]
                        try:
                            result = function_call(fn_name, args, self.functions)
                            self.chat.add_message(Role.FUNCTION.value, result, name=fn_name)
                        except FunctionCallError as e:
                            self.chat.add_message(
                                Role.FUNCTION.value, "Error: " + str(e), name=fn_name
                            )

            except KeyboardInterrupt:
                break
            except Exception as e:
                print("Error: " + str(e))

    @retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
    def reply(self, force_function: str = "auto", insert_functions=True, stream=False):
        "force_function can be 'auto', 'none', or a function name"
        if force_function != "none" and force_function != "auto":
            assert force_function in self.functions, f"force_function=`{force_function}` not found"

        response = openai.ChatCompletion.create(
            model=self.model,
            messages=self.chat.get_messages(),
            functions=(self.schemas or None) if insert_functions else None,
            function_call={"name": force_function} if force_function != "auto" else None,
            # TODO: streaming... Need to add partial message printing
        )
        return Message(**response["choices"][0]["message"])
