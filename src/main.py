"""
Main Entrypoint of the batch. This module should parse and command line arguments,
instantiate the TrixieJob, and call "run_batch".
"""
import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from loguru import logger


from batch_runner import TrixieJob

def main(args: Sequence[str] | None = None) -> int:
    """The main entrypoint of the application"""
    parser = ArgumentParser(description="Process recruiter leads.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan the e-mails but do not send any notifications or make any db commits"
    )
    try:
        logger.info("Executing Trixie Job")
        tj = TrixieJob()
        tj.run_job()
        return 0 # Successful exit code
    except Exception:
        logger.exception("An unexpected error occurred!")
        return 1




if __name__ == "__main__":
    sys.exit(main())
