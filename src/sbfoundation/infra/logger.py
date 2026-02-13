from __future__ import annotations
import copy
from datetime import datetime
import logging
import os
from pathlib import Path
import sys
from typing import Callable, Optional
from typing import Protocol, runtime_checkable

from sbfoundation.folders import Folders
from sbfoundation.settings import *


@runtime_checkable
class SBLogger(Protocol):
    """logging.Logger extended with log_section."""

    def debug(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def info(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def warning(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def error(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def critical(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def exception(self, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def log(self, level: int, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None: ...
    def log_section(self, run_id: str, section: str) -> None: ...


class _FixedWidthFormatter(logging.Formatter):
    """Formatter that normalises levelname to 7 chars and name to 30 chars.

    Using ljust in Python code is more reliable than relying on %-7s in the
    format string, which can be bypassed by loggers created outside LoggerFactory.
    """

    _LEVELNAME_WIDTH = 7
    _NAME_WIDTH = 30

    def format(self, record: logging.LogRecord) -> str:
        r = copy.copy(record)
        r.levelname = r.levelname.ljust(self._LEVELNAME_WIDTH)
        r.name = r.name.ljust(self._NAME_WIDTH)
        return super().format(r)


class LoggerFactory:
    """Centralized logging that standardizes handler reuse and log levels."""

    def __init__(self, log_path: Optional[Path] | None = None, log_level: Optional[str] | None = None):
        self._explicit_log_level = log_level
        self.log_dir = log_path or Folders.logs_absolute_path()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"logs_{datetime.now().date()}.txt"
        self.format = "%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s"

    def create_logger(self, name: str) -> SBLogger:
        logger = logging.getLogger(name)
        target_level = self._determine_log_level()
        logger.setLevel(target_level)
        logger.propagate = False  # avoid duplicate writes via root logger

        formatter = _FixedWidthFormatter(self.format)
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

        def _log_section(self: logging.Logger, run_id: str, section: str) -> None:
            self.info(f"========== {section} | run_id={run_id} ==========")

        logging.Logger.log_section = _log_section  # type: ignore[attr-defined]

        if not hasattr(logging.Logger, "_sb_original_info"):
            logging.Logger._sb_original_info = logging.Logger.info  # type: ignore[attr-defined]
            logging.Logger._sb_original_debug = logging.Logger.debug  # type: ignore[attr-defined]
            logging.Logger._sb_original_warning = logging.Logger.warning  # type: ignore[attr-defined]
            logging.Logger._sb_original_error = logging.Logger.error  # type: ignore[attr-defined]
            logging.Logger._sb_original_critical = logging.Logger.critical  # type: ignore[attr-defined]
            logging.Logger._sb_original_exception = logging.Logger.exception  # type: ignore[attr-defined]
            logging.Logger._sb_original_log = logging.Logger.log  # type: ignore[attr-defined]

            def _info(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_info(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _debug(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_debug(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _warning(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_warning(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _error(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_error(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _critical(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_critical(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _exception(self: logging.Logger, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_exception(self, msg, *args, **kwargs)  # type: ignore[attr-defined]

            def _log(self: logging.Logger, level: int, msg: object, *args: object, run_id: str | None = None, **kwargs: object) -> None:  # type: ignore[misc]
                if run_id is not None:
                    msg = f"run_id={run_id} | {msg}"
                logging.Logger._sb_original_log(self, level, msg, *args, **kwargs)  # type: ignore[attr-defined]

            logging.Logger.info = _info  # type: ignore[assignment]
            logging.Logger.debug = _debug  # type: ignore[assignment]
            logging.Logger.warning = _warning  # type: ignore[assignment]
            logging.Logger.error = _error  # type: ignore[assignment]
            logging.Logger.critical = _critical  # type: ignore[assignment]
            logging.Logger.exception = _exception  # type: ignore[assignment]
            logging.Logger.log = _log  # type: ignore[assignment]

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


__all__ = ["LoggerFactory", "SBLogger"]
