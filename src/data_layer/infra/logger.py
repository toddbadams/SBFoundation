from __future__ import annotations
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from typing import Callable, Optional

from folders import Folders
from settings import *


class LoggerFactory:
    """Centralized logging that standardizes handler reuse and log levels."""

    def __init__(self, log_path: Optional[Path] | None = None, log_level: Optional[str] | None = None):
        self._explicit_log_level = log_level
        self.log_dir = log_path or Folders.logs_absolute_path()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"logs_{datetime.now().date()}.txt"
        self.format = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"

    def create_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        target_level = self._determine_log_level()
        logger.setLevel(target_level)
        logger.propagate = False  # avoid duplicate writes via root logger

        formatter = logging.Formatter(self.format)
        stream_handler = self._ensure_handler(
            logger,
            logging.StreamHandler,
            lambda: logging.StreamHandler(sys.stdout),
            target_level,
            formatter,
        )
        stream_handler.setLevel(target_level)
        stream_handler.setFormatter(formatter)

        file_handler = self._ensure_handler(
            logger,
            logging.FileHandler,
            lambda: logging.FileHandler(self.log_file, mode="a", encoding="utf-8", delay=False),
            target_level,
            formatter,
        )
        file_handler.setLevel(target_level)
        file_handler.setFormatter(formatter)

        if getattr(file_handler, "stream", None) is None:
            file_handler.stream = file_handler._open()

        return logger

    def _determine_log_level(self) -> int:
        if self._explicit_log_level:
            return logging.getLevelName(self._explicit_log_level)
        is_dev = os.getenv("ENV") == "DEV"
        return logging.INFO if is_dev else logging.WARN

    @staticmethod
    def _ensure_handler(
        logger: logging.Logger,
        handler_type: type[logging.Handler],
        factory: Callable[[], logging.Handler],
        level: int,
        formatter: logging.Formatter,
    ) -> logging.Handler:
        matches = [handler for handler in logger.handlers if isinstance(handler, handler_type)]
        if matches:
            primary = matches[0]
            for extra in matches[1:]:
                logger.removeHandler(extra)
            return primary
        handler = factory()
        logger.addHandler(handler)
        return handler


__all__ = ["LoggerFactory"]
