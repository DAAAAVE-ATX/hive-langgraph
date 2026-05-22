"""BYOLLM factory. Selects a LangChain chat model by provider."""

import os


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OLLAMA_MODEL = "llama3.1"


def get_llm(provider=None, model=None):
    """Return a configured LangChain chat model.

    Args:
        provider: ``anthropic`` or ``ollama``. Defaults to ``HIVE_LG_PROVIDER`` env
            var, then to ``anthropic``.
        model: Optional override of the provider's default model identifier.

    Returns:
        A LangChain ``BaseChatModel`` instance.

    Raises:
        RuntimeError: If Ollama is selected but the local server cannot be reached,
            or if an unknown provider is requested.
    """
    if provider is None:
        provider = os.getenv("HIVE_LG_PROVIDER", "anthropic").strip().lower()

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model or DEFAULT_ANTHROPIC_MODEL)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import urllib.request
            urllib.request.urlopen(f"{base_url}/api/tags", timeout=2).read()
        except Exception as exc:
            raise RuntimeError(
                f"Ollama provider selected but server at {base_url} is unreachable. "
                "Start Ollama or switch HIVE_LG_PROVIDER back to anthropic. "
                "See .env.example for configuration."
            ) from exc

        return ChatOllama(model=model or DEFAULT_OLLAMA_MODEL, base_url=base_url)

    raise RuntimeError(
        f"Unknown HIVE_LG_PROVIDER '{provider}'. Supported: anthropic, ollama."
    )
