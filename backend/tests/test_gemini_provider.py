import pytest

from app.providers.gemini import GeminiProvider


@pytest.fixture(autouse=True)
def clear_gemini_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "")


def test_gemini_list_models_without_key_is_unavailable() -> None:
    provider = GeminiProvider()
    models = provider.list_models()
    assert len(models) == 1
    assert models[0].available is False
    assert models[0].id == "gemini:1.5-flash"
    assert models[0].reason and "GEMINI_API_KEY" in models[0].reason


def test_gemini_generate_without_key_returns_missing_key() -> None:
    provider = GeminiProvider()
    import asyncio

    result = asyncio.run(provider.generate("gemini:1.5-flash", "hi", temperature=0, max_tokens=1))
    assert result.ok is False
    assert result.error_code == "missing_api_key"
