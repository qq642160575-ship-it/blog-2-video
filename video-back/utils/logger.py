import json
import logging
from typing import Any


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOGGER_NAME = "video_back"


def setup_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger(LOGGER_NAME)
    if root_logger.handlers:
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root_logger.addHandler(handler)
    root_logger.setLevel(level)
    root_logger.propagate = False


def get_logger(name: str | None = None) -> logging.Logger:
    setup_logging()
    if not name:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def log_event(level: str = "info", **fields: Any) -> None:
    logger = get_logger()
    message = json.dumps(fields, ensure_ascii=False, default=str)
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message)
