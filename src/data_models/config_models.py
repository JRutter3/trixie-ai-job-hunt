"""Module for the config models."""

import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    api_key: str
    gm_bot_id: str
    ai_model: str
    sys_prompt_path: Path = Path("/app/cfg/recruiter_prompt.txt")
    summary_template_path: Path = Path("/app/cfg/summary_template.txt")
    gmail_credentials_json: str
    gmail_token_json: str


def parse_config(config_location: Path) -> AppConfig:
    """Parses the config file and env variabels in to a config object."""
    with open(config_location, "rb") as f:
        result_dict = tomllib.load(f)
        return AppConfig.model_validate(result_dict)
