"""
Main Entrypoint of the batch. This module should parse and command line arguments,
instantiate the TrixieJob, and call "run_batch".
"""

import asyncio
import os
import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from batch_runner import TrixieJob
from data_models.config_models import parse_config


def main(args: Sequence[str] | None = None) -> int:
    """The main entrypoint of the application"""
    parser = ArgumentParser(description="Process recruiter leads.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Scan the e-mails but do not send any notifications or make any db commits"
        ),
    )
    parsed_args = parser.parse_args()
    config_location = os.getenv("CONFIG_PATH")
    if config_location is None:
        raise ValueError("No config location given.")
    try:
        logger.info("Loading config file from {}", config_location)
        cfg = parse_config(Path(config_location))
        logger.info("Executing Trixie Job")
        tj = TrixieJob(cfg, parsed_args.dry_run)  # type: ignore
        asyncio.run(tj.run_job())
        return 0  # Successful exit code
    except Exception:
        logger.exception("An unexpected error occurred!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
