"""Canned LLM response fixtures for testing."""


class _Obj:
    """Simple namespace that allows attribute access from a dict."""

    def __init__(self, d: dict):
        for k, v in d.items():
            setattr(self, k, _Obj(v) if isinstance(v, dict) else v)

    def __getitem__(self, key):
        return getattr(self, key)


def mock_chat_response(content: str = "Hello! How can I help?"):
    """Return a mock LiteLLM completion response with attribute access."""
    return _Obj({
        "choices": [
            _Obj({
                "message": _Obj({
                    "role": "assistant",
                    "content": content,
                }),
                "finish_reason": "stop",
                "index": 0,
            })
        ],
        "model": "ollama/llama3",
        "usage": _Obj({"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}),
    })


def mock_classification_response(intent: str, extracted_content: str = ""):
    """Return a mock LiteLLM response for intent classification."""
    import json

    payload = {"intent": intent, "extracted_content": extracted_content}
    return mock_chat_response(json.dumps(payload))


def mock_embedding_response(dim: int = 768):
    """Return a mock LiteLLM embedding response structure."""
    return type(
        "EmbeddingResponse",
        (),
        {"data": [{"embedding": [0.01] * dim}]},
    )()
