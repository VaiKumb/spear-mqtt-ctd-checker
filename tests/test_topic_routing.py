"""Tests for CTD MQTT topic routing and plausibility callbacks."""

from __future__ import annotations

from datetime import UTC, datetime

from unittest.mock import MagicMock

from spear_mqtt_ctd import ctd_pb2
from spear_mqtt_ctd.config import BrokerConfig
from spear_mqtt_ctd.mqtt_client import CtdMqttClient
from spear_mqtt_ctd.parser import is_ctd_topic


def _ctd_payload(temperature: float, when: datetime | None = None) -> bytes:
    ctd = ctd_pb2.CtdSensor()
    ctd.temperature = temperature
    if when is not None:
        ctd.stamp.FromDatetime(when)
    return ctd.SerializeToString()


def _make_client(**kwargs) -> CtdMqttClient:
    return CtdMqttClient(
        config_path="unused",
        buoy_uuid="abc-123",
        broker_config=BrokerConfig(
            host="example.com",
            port=8883,
            user="user",
            password="pass",
        ),
        **kwargs,
    )


def test_is_ctd_topic_accepts_ctd_path() -> None:
    assert is_ctd_topic("devices/abc-123/sensors/ctd")


def test_is_ctd_topic_rejects_status_path() -> None:
    assert not is_ctd_topic("devices/abc-123/status")


def test_is_ctd_topic_rejects_other_sensor() -> None:
    assert not is_ctd_topic("devices/abc-123/sensors/ais")


def test_handle_message_ignores_non_ctd_topic() -> None:
    client = _make_client()
    handled = client.handle_message("devices/abc-123/status", b"payload")
    assert handled is False


def test_handle_message_plausible_ctd_topic() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    payload = _ctd_payload(12.0, now)

    on_plausible = MagicMock()
    on_implausible = MagicMock()
    client = _make_client(on_plausible=on_plausible, on_implausible=on_implausible)

    topic = "devices/abc-123/sensors/ctd"
    assert client.handle_message(topic, payload, now=now) is True
    on_plausible.assert_called_once()
    on_implausible.assert_not_called()
    assert client.last_status is not None
    assert client.last_status.plausible is True
    assert client.last_status.temperature == 12.0

    # Repeated plausible readings should not invoke callbacks again.
    assert client.handle_message(topic, payload, now=now) is True
    on_plausible.assert_called_once()
    on_implausible.assert_not_called()


def test_handle_message_notifies_on_plausibility_change() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    plausible_payload = _ctd_payload(12.0, now)
    implausible_payload = _ctd_payload(float("nan"), now)

    on_plausible = MagicMock()
    on_implausible = MagicMock()
    client = _make_client(on_plausible=on_plausible, on_implausible=on_implausible)

    topic = "devices/abc-123/sensors/ctd"
    client.handle_message(topic, plausible_payload, now=now)
    client.handle_message(topic, implausible_payload, now=now)
    client.handle_message(topic, implausible_payload, now=now)
    client.handle_message(topic, plausible_payload, now=now)

    on_plausible.assert_called()
    on_implausible.assert_called()
    assert on_plausible.call_count == 2
    assert on_implausible.call_count == 1
    assert on_implausible.call_args.args[1] == "not_finite"


def test_handle_message_detects_unstable_jump() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    first = _ctd_payload(5.0, now)
    jump = _ctd_payload(15.0, now)

    on_plausible = MagicMock()
    on_implausible = MagicMock()
    client = _make_client(on_plausible=on_plausible, on_implausible=on_implausible, max_step_c=2.0)

    topic = "devices/abc-123/sensors/ctd"
    client.handle_message(topic, first, now=now)
    client.handle_message(topic, jump, now=now)

    on_plausible.assert_called_once()
    on_implausible.assert_called_once()
    assert on_implausible.call_args.args[1] == "unstable"
