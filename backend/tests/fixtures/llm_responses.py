"""Canned LLM response fixtures for testing."""


def mock_chat_response(content: str = "Hello! How can I help?"):
    """Return a mock LiteLLM completion response structure."""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "model": "ollama/llama3",
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def mock_embedding_response(dim: int = 768):
    """Return a mock LiteLLM embedding response structure."""
    return type(
        "EmbeddingResponse",
        (),
        {"data": [{"embedding": [0.01] * dim}]},
    )()
