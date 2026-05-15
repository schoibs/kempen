import logging
import os


def configure_logging() -> None:
    logging.basicConfig(
        level="INFO",
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
