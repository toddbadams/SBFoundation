from __future__ import annotations

from datetime import date
import logging
from pathlib import Path

import pytest

from sbfoundation.infra.logger import LoggerFactory


def _count_handler_types(logger: logging.Logger, handler_type: type[logging.Handler]) -> int:
    return sum(1 for handler in logger.handlers if type(handler) is handler_type)


def test_env_drives_log_level(monkeypatch, patch_folders) -> None:
    monkeypatch.setenv("ENV", "DEV")
    factory = LoggerFactory()
    dev_logger = factory.create_logger("infra-test-dev")
    assert dev_logger.level == logging.INFO

    monkeypatch.setenv("ENV", "PROD")
    prod_logger = factory.create_logger("infra-test-prod")
    assert prod_logger.level == logging.WARN


def test_logger_deduplicates_handlers(monkeypatch, patch_folders) -> None:
    factory = LoggerFactory()
    name = "infra-test-duplication"
    logger = factory.create_logger(name)
    assert _count_handler_types(logger, logging.StreamHandler) == 1
    assert _count_handler_types(logger, logging.FileHandler) == 1
    second = factory.create_logger(name)
    assert len(second.handlers) == len(logger.handlers)
    assert _count_handler_types(second, logging.StreamHandler) == 1
    assert _count_handler_types(second, logging.FileHandler) == 1


def test_custom_log_path(monkeypatch, tmp_path, patch_folders: tuple[Path, Path]) -> None:
    log_root = tmp_path / "logs"
    factory = LoggerFactory(log_path=log_root)
    logger = factory.create_logger("infra-test-custom")
    assert _count_handler_types(logger, logging.FileHandler) == 1
    expected_file = list(log_root.glob("logs_*.txt"))
    assert expected_file, "Expected a log file to be created"
