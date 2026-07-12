"""Model providers supported by Cassiopeia."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import SecretStr
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider


class ProviderName(StrEnum):
    OPENAI = "openai"
    GOOGLE = "google"


@dataclass(frozen=True)
class AIProvider:
    """Create Pydantic AI models using one provider credential."""

    name: ProviderName
    api_key: SecretStr

    def model(self, model_name: str) -> Model:
        key = self.api_key.get_secret_value()

        match self.name:
            case ProviderName.OPENAI:
                return OpenAIResponsesModel(
                    model_name,
                    provider=OpenAIProvider(api_key=key),
                )
            case ProviderName.GOOGLE:
                return GoogleModel(
                    model_name,
                    provider=GoogleProvider(api_key=key),
                )
