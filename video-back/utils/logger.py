import json
import logging
from typing import Any


logger = logging.getLogger("video_back")


def log_event(**fields: Any) -> None:
    if not logger.handlers:
        logging.basicConfig(level=logging.INFO)
    logger.info(json.dumps(fields, ensure_ascii=False))
