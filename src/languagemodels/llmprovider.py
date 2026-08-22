import logging

from langchain_groq import ChatGroq
from src.config.settings import settings
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class DummyLLM:
    """Fallback model used when no credentials are configured."""

    def invoke(self, messages):
        return type(
            "Response",
            (),
            {"content": "LLM unavailable: configure an API key to enable analysis."},
        )()


def get_llm_instance(provider_name: str):
    """Create an LLM instance for the requested provider."""
    return LLMProvider(provider_name).get_llm_instance()


class LLMProvider():
    """
    A class to manage the LLM provider configuration and instantiation.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.groq_temperature = settings.GROQ_LLM_TEMPERATURE
        self.openai_temperature = settings.OPENAI_LLM_TEMPERATURE
        self.groq_api_key = settings.GROQ_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.configured_openai_model = settings.OPENAI_LLM_MODEL
        self.configured_groq_model = settings.GROQ_LLM_MODEL
        self.openai_api_base = settings.OPENAI_API_BASE

    def get_llm_instance(self):
        """
        Returns an instance of the LLM based on the specified provider.

        Returns:
            llm model based on the request.
        """
        try:
            if self.model_name.startswith("groq"):
                logger.info("Creating GROQ LLM instance with model: %s", self.configured_groq_model)
                if not self.groq_api_key:
                    raise ValueError("GROQ_API_KEY is not configured.")
                return ChatGroq(
                    model=self.configured_groq_model,
                    temperature=self.groq_temperature,
                    api_key=self.groq_api_key,
                    )
            elif (self.model_name.startswith("openai")):
                logger.info("Creating OpenAI LLM instance with model: %s", self.configured_openai_model)
                if not self.openai_api_key:
                    return DummyLLM()
                return ChatOpenAI(
                    model=self.configured_openai_model,
                    temperature=self.openai_temperature,
                    api_key=self.openai_api_key,
                    base_url=self.openai_api_base,
                )
            else:
                raise ValueError(f"Unsupported model: {self.model_name}")
        except Exception as e:
            logger.exception("Error creating LLM instance: %s", e)
            return DummyLLM()        