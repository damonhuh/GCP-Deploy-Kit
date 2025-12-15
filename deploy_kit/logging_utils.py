import logging
import sys


def setup_logging(verbosity: int = 0) -> None:
    level = logging.INFO
    if verbosity >= 1:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


