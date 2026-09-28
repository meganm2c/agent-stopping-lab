"""Environment configuration. Credentials are never included in run records."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    model_provider: str
    model_name: str
    api_key: str = field(repr=False)
    azure_endpoint: str | None = None
    azure_api_version: str = "2024-10-21"
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
        if provider not in ("openai", "azure"):
            raise ValueError("MODEL_PROVIDER must be openai or azure")
        model = os.getenv("MODEL_NAME", "").strip()
        key_name = "OPENAI_API_KEY" if provider == "openai" else "AZURE_OPENAI_API_KEY"
        key = os.getenv(key_name, "").strip()
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip() or None
        missing = [name for name, value in (("MODEL_NAME", model), (key_name, key)) if not value]
        if provider == "azure" and not endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if missing:
            raise ValueError("Set " + ", ".join(missing) + " in .env before running a live agent")
        temperature = float(os.getenv("MODEL_TEMPERATURE", "0"))
        if not 0 <= temperature <= 2:
            raise ValueError("MODEL_TEMPERATURE must be between 0 and 2")
        return cls(provider, model, key, endpoint, os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"), temperature)


def create_client(settings: Settings):
    from agent_framework.openai import OpenAIChatCompletionClient
    kwargs = {"model": settings.model_name, "api_key": settings.api_key}
    if settings.model_provider == "azure":
        kwargs.update(azure_endpoint=settings.azure_endpoint, api_version=settings.azure_api_version)
    return OpenAIChatCompletionClient(**kwargs)
