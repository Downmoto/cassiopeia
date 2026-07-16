import pytest
from pydantic_ai.models.test import TestModel

from ethos.config import EthosSettings
from ethos.provider import AIProvider
from ethos.runtime import run_prompt


def test_run_prompt_returns_model_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = EthosSettings.model_validate(
        {
            "provider": {"name": "openai", "model_name": "gpt-5-mini"},
            "keys": {"openai_api_key": "test-key"},
        }
    )
    monkeypatch.setattr(
        AIProvider,
        "model",
        lambda _provider, _model_name: TestModel(
            custom_output_text="hello from ethos"
        ),
    )

    output = run_prompt("hello", settings)

    assert output == "hello from ethos"


def test_run_prompt_requires_provider_selection() -> None:
    with pytest.raises(ValueError, match="ETHOS_PROVIDER__NAME is required"):
        run_prompt("hello", EthosSettings.defaults())
