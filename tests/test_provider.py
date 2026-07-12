from pydantic import SecretStr
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIResponsesModel

from cassiopeia.provider import AIProvider, ProviderName


def test_openai_provider_creates_responses_model() -> None:
    provider = AIProvider(ProviderName.OPENAI, SecretStr("test-key"))

    model = provider.model("gpt-5-mini")

    assert isinstance(model, OpenAIResponsesModel)
    assert model.model_name == "gpt-5-mini"


def test_google_provider_creates_google_model() -> None:
    provider = AIProvider(ProviderName.GOOGLE, SecretStr("test-key"))

    model = provider.model("gemini-2.5-flash")

    assert isinstance(model, GoogleModel)
    assert model.model_name == "gemini-2.5-flash"


def test_provider_does_not_expose_api_key_in_repr() -> None:
    provider = AIProvider(ProviderName.OPENAI, SecretStr("secret-key"))

    assert "secret-key" not in repr(provider)
