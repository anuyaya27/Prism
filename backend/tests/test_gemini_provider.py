from app.providers.gemini import GeminiProvider


def test_gemini_disabled_list_models() -> None:
    provider = GeminiProvider()
    models = provider.list_models()
    assert len(models) == 1
    assert models[0].available is False
    assert models[0].reason and "disabled" in models[0].reason.lower()


def test_gemini_disabled_generate() -> None:
    provider = GeminiProvider()
    import asyncio

    result = asyncio.run(provider.generate("gemini:any", "hi", temperature=0, max_tokens=1))
    assert result.ok is False
    assert result.error_code == "GEMINI_DISABLED"
