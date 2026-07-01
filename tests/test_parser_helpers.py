"""Tests for CTD topic parsing helpers."""

from __future__ import annotations

from spear_mqtt_ctd.parser import buoy_uuid_from_ctd_topic, is_ctd_topic


def test_buoy_uuid_from_ctd_topic() -> None:
    assert buoy_uuid_from_ctd_topic("devices/abc-123/sensors/ctd") == "abc-123"


def test_buoy_uuid_from_ctd_topic_rejects_non_ctd_topic() -> None:
    assert buoy_uuid_from_ctd_topic("devices/abc-123/status") is None
    assert not is_ctd_topic("devices/abc-123/status")
