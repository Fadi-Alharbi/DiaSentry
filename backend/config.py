"""
DiaSentry — Centralized Configuration
=======================================
All system settings loaded from environment variables with sensible defaults.
Uses Pydantic BaseSettings for type-safe configuration management.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv(".env", override=True)


class Settings(BaseSettings):
    """
    Application settings loaded from .env file or environment variables.
    Grouped by subsystem for clarity.
    """

    # ═══════════════════════════════════════════════════════════════
    #  LLM Configuration
    # ═══════════════════════════════════════════════════════════════
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_TOKENS: int = 2048

    # ═══════════════════════════════════════════════════════════════
    #  Virtual CGM Simulator Configuration
    # ═══════════════════════════════════════════════════════════════
    SIM_INTERVAL_SEC: float = 5.0          # Seconds between CGM readings (real-time)
    SIM_INTERNAL_STEP_MIN: float = 1.0     # Internal ODE integration step (minutes)
    SIM_READINGS_PER_OUTPUT: int = 5       # 5 internal 1-min steps = 1 output every 5 sim-minutes
    SENSOR_NOISE_STD: float = 2.5          # Gaussian noise σ (mg/dL) for sensor inaccuracy
    ISF_LAG_MINUTES: float = 12.0          # Interstitial fluid lag behind blood glucose

    # Bergman Minimal Model Parameters
    BERGMAN_P1: float = 0.028              # Glucose effectiveness (1/min)
    BERGMAN_P2: float = 0.025              # Rate of insulin action decay (1/min)
    BERGMAN_P3: float = 0.000013           # Insulin sensitivity (1/min per μU/mL)
    BERGMAN_GB: float = 110.0              # Basal glucose (mg/dL)
    BERGMAN_IB: float = 10.0               # Basal insulin (μU/mL)
    BERGMAN_N: float = 0.23                # Insulin clearance rate (1/min)

    # ═══════════════════════════════════════════════════════════════
    #  Clinical Thresholds (ADA Standards of Care)
    # ═══════════════════════════════════════════════════════════════
    HYPO_CRITICAL: float = 54.0            # Level 2 hypoglycemia (mg/dL)
    HYPO_THRESHOLD: float = 70.0           # Level 1 hypoglycemia (mg/dL)
    TARGET_LOW: float = 70.0               # Target range lower bound
    TARGET_HIGH: float = 180.0             # Target range upper bound
    HYPER_THRESHOLD: float = 180.0         # Hyperglycemia threshold
    HYPER_CRITICAL: float = 250.0          # Severe hyperglycemia
    ANOMALY_RATE: float = 2.0              # Unexplained change rate (mg/dL/min)

    # ═══════════════════════════════════════════════════════════════
    #  Server Configuration
    # ═══════════════════════════════════════════════════════════════
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "*"

    # ═══════════════════════════════════════════════════════════════
    #  History Buffer Sizes
    # ═══════════════════════════════════════════════════════════════
    HISTORY_BUFFER_SIZE: int = 72          # 6 hours of 5-min readings
    PREDICTION_HORIZON_MIN: int = 60       # 60-minute forecast
    PREDICTION_STEPS: int = 12             # 12 x 5-min forecast points
    CHAT_MEMORY_SIZE: int = 10             # Last N chat messages to retain

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @property
    def is_gemini(self) -> bool:
        return self.OPENAI_API_KEY.startswith("AQ.") or self.OPENAI_API_KEY.startswith("AIza") or "gemini" in self.OPENAI_MODEL.lower()

    @property
    def is_ollama(self) -> bool:
        """True when using a local Ollama server (via OPENAI_BASE_URL or ollama API key)."""
        return (
            self.OPENAI_API_KEY == "ollama"
            or "localhost:11434" in self.OPENAI_BASE_URL
            or "127.0.0.1:11434" in self.OPENAI_BASE_URL
        )

    @property
    def is_qwen(self) -> bool:
        return "qwen" in self.OPENAI_MODEL.lower() or self.OPENAI_API_KEY.startswith("sk-ws-")

    @property
    def is_openrouter(self) -> bool:
        return self.OPENAI_API_KEY.startswith("sk-or-v1-")

    @property
    def effective_model(self) -> str:
        if self.is_gemini and "gpt" in self.OPENAI_MODEL:
            return "gemini-2.5-flash"
        if self.is_qwen and "gpt" in self.OPENAI_MODEL:
            return "qwen-plus"
        return self.OPENAI_MODEL

    @property
    def client_kwargs(self) -> dict:
        kwargs = {"api_key": self.OPENAI_API_KEY}
        # OPENAI_BASE_URL always wins — covers Ollama, LM Studio, vLLM, etc.
        if self.OPENAI_BASE_URL:
            kwargs["base_url"] = self.OPENAI_BASE_URL
        elif self.is_openrouter:
            kwargs["base_url"] = "https://openrouter.ai/api/v1"
        elif self.is_gemini:
            kwargs["base_url"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
        elif self.is_qwen:
            kwargs["base_url"] = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        return kwargs


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton accessor for application settings."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear the cached settings so a new Settings() is created on next call."""
    get_settings.cache_clear()
