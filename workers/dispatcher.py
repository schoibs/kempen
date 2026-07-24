from __future__ import annotations

import argparse
import logging
import signal
import threading

from app_config import get_settings
from infrastructure import check_database_and_migrations, check_redis
from logging_config import configure_logging


logger = logging.getLogger(__name__)


class Dispatcher:
    """Initial process shell; outbox dispatch arrives in a later phase."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._stop_event = threading.Event()

    def check_dependencies(self) -> None:
        check_database_and_migrations()
        check_redis()

    def run(self, *, once: bool = False) -> None:
        while not self._stop_event.is_set():
            try:
                self.check_dependencies()
            except Exception:
                logger.exception("Dispatcher dependency check failed; will retry.")
                if once:
                    raise
            else:
                logger.info(
                    "Dispatcher heartbeat: environment=%s fake_provider_mode=%s",
                    self.settings.environment,
                    self.settings.fake_provider_mode,
                )
            if once:
                return
            self._stop_event.wait(self.settings.dispatcher_interval_sec)

    def stop(self, *_: object) -> None:
        self._stop_event.set()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the campaign dispatcher shell.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check dependencies once and exit.",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(level=settings.log_level)
    dispatcher = Dispatcher()
    signal.signal(signal.SIGTERM, dispatcher.stop)
    signal.signal(signal.SIGINT, dispatcher.stop)
    dispatcher.run(once=args.once)


if __name__ == "__main__":
    main()
