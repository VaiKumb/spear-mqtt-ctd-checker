"""Tests for terminal formatting and heartbeat status."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from spear_mqtt_ctd.heartbeat import print_reading_status
from spear_mqtt_ctd.status import ReadingStatus
from spear_mqtt_ctd.terminal import (
    GREEN,
    RED,
    YELLOW,
    format_implausible,
    format_plausible,
    format_waiting,
)


def test_format_plausible_includes_green() -> None:
    text = format_plausible(12.3)
    assert "PLAUSIBLE" in text
    assert "12.300 C" in text
    assert GREEN in text


def test_format_implausible_includes_red() -> None:
    text = format_implausible(87.2, "above_range")
    assert "IMPLAUSIBLE (above_range)" in text
    assert RED in text


def test_format_waiting_includes_yellow() -> None:
    text = format_waiting()
    assert "WAITING" in text
    assert YELLOW in text


def test_print_reading_status_waiting(capsys) -> None:
    client = MagicMock()
    client.last_status = None
    print_reading_status(client)
    captured = capsys.readouterr()
    assert "WAITING" in captured.out


def test_print_reading_status_plausible(capsys) -> None:
    client = MagicMock()
    client.last_status = ReadingStatus(
        temperature=12.3,
        plausible=True,
        reason=None,
        received_at=datetime.now(tz=UTC),
    )
    print_reading_status(client)
    captured = capsys.readouterr()
    assert "PLAUSIBLE" in captured.out
    assert GREEN in captured.out
