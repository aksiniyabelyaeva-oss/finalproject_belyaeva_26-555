import logging
import time

from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("parser_service")


def run_scheduler(updater: RatesUpdater, interval_seconds: int, on_report=None) -> None:
    """Обновляет курсы каждые interval_seconds секунд, пока не нажмут Ctrl+C."""
    logger.info("Scheduler started, interval: %s s", interval_seconds)
    try:
        while True:
            report = updater.run_update()
            if on_report is not None:
                on_report(report)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
