"""Configuration related to environment variables."""

import os
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Environment configuration with validation."""

    azure_api_key: str
    azure_endpoint: str
    azure_api_version: str
    neon_mcp_token: Optional[str] = None
    gemini_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "EnvironmentConfig":
        """Create config from environment variables with validation."""
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

        if not api_key:
            logger.warning("AZURE_OPENAI_API_KEY environment variable not set.")
            # Allow execution without Azure key for testing/other modes, but log
            # Or raise ValueError("AZURE_OPENAI_API_KEY must be set") if mandatory
            api_key = ""  # Provide a default or handle appropriately

        if not endpoint:
            logger.warning("AZURE_OPENAI_ENDPOINT environment variable not set.")
            # raise ValueError("AZURE_OPENAI_ENDPOINT must be set")
            endpoint = ""  # Provide a default or handle appropriately

        config_instance = cls(
            azure_api_key=api_key,
            azure_endpoint=endpoint,
            azure_api_version=os.getenv(
                "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
            ),
            neon_mcp_token=os.getenv("NEON_MCP_TOKEN"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
        )
        logger.info("EnvironmentConfig loaded.")
        # Log which optional keys are present
        if config_instance.neon_mcp_token:
            logger.info("NEON_MCP_TOKEN found.")
        if config_instance.gemini_api_key:
            logger.info("GEMINI_API_KEY found.")
        return config_instance


# Load environment config immediately upon import
try:
    env_config = EnvironmentConfig.from_env()
except ValueError as e:
    logger.critical(f"Fatal environment configuration error: {e}", exc_info=True)
    # Depending on severity, you might want to exit or raise further
    # For now, create a dummy config to prevent downstream NoneErrors, but log critical
    env_config = EnvironmentConfig(
        azure_api_key="", azure_endpoint="", azure_api_version=""
    )
