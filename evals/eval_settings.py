from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class EvaluationSettings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=PROJECT_ROOT / ".env",
		env_file_encoding="utf-8",
		extra="ignore",
		case_sensitive=False,
	)

	langsmith_api_key: str | None = Field(
		default=None,
		validation_alias="LANGSMITH_API_KEY",
	)
	langsmith_project: str = Field(
		default="brokerage-chatbot-evals",
		validation_alias="LANGSMITH_PROJECT",
	)
	langsmith_dataset: str = Field(
		default="brokerage-chatbot-smoke",
		validation_alias="LANGSMITH_DATASET",
	)
	chatbot_api_url: str = Field(
		default="http://127.0.0.1:8000/api/v1/brokeragent/broker-chat",
		validation_alias="CHATBOT_API_URL",
	)


settings = EvaluationSettings()
