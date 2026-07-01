"""Tests for CTD payload parsing."""

from __future__ import annotations

import pytest

from spear_mqtt_ctd import ctd_pb2
from spear_mqtt_ctd.parser import CtdParseError, extract_temperature, parse_ctd_payload


def _serialize_ctd(temperature: float) -> bytes:
    ctd = ctd_pb2.CtdSensor()
    ctd.temperature = temperature
    return ctd.SerializeToString()


def test_parse_ctd_payload_round_trip() -> None:
    payload = _serialize_ctd(12.34)
    ctd = parse_ctd_payload(payload)
    assert extract_temperature(ctd) == pytest.approx(12.34)


def test_parse_invalid_payload_raises() -> None:
    with pytest.raises(CtdParseError):
        parse_ctd_payload(b"not-a-valid-protobuf")
