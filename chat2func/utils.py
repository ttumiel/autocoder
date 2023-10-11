def approx_token_count(text: str):
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return round(1.4 * len(text.split()))
