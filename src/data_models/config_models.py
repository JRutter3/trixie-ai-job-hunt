"""Module for the config models."""

import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    api_key: str
    ai_model: str
    sys_prompt_path: Path


def parse_config(config_location: Path) -> AppConfig:
    """Parses the config file and env variabels in to a config object."""
    with open(config_location, "rb") as f:
        result_dict = tomllib.load(f)
        return AppConfig.model_validate(result_dict)
