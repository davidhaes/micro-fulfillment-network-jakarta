# Logger setup
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from micro_fulfillment_network_jakarta.config import get_settings

_CONFIGURED = False


def get_logger(name: str = "micro_fulfillment_network_jakarta"):
    """Return a configured Loguru logger with console and Markdown file sinks."""
    global _CONFIGURED

    settings = get_settings()
    log_path = settings.outputs_dir / "run_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not _CONFIGURED:
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {extra[module]} | {message}",
        )
        logger.add(
            log_path,
            level="INFO",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} UTC | {level} | {extra[module]} | {message}",
            enqueue=True,
        )
        _CONFIGURED = True

    return logger.bind(module=name)


def append_markdown_log(message: str) -> None:
    """Append a timestamped Markdown log entry to outputs/run_log.md."""
    settings = get_settings()
    log_path = settings.outputs_dir / "run_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(f"\n* {timestamp}: {message}\n")
