from .api import ChatModel


def approx_token_count(text: str, model: str = ChatModel.GPT4.value):
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        return round(1.35 * len(text.split()))
