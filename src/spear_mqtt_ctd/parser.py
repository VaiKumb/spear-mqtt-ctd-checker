"""Parse CTD protobuf payloads."""

from __future__ import annotations

from google.protobuf.message import DecodeError

from spear_mqtt_ctd import ctd_pb2

CTD_TOPIC_SUFFIX = "/sensors/ctd"


class CtdParseError(ValueError):
    """Raised when a payload cannot be deserialized as CtdSensor."""


def is_ctd_topic(topic: str) -> bool:
    """Return True if topic matches devices/<uuid>/sensors/ctd."""
    parts = topic.split("/")
    return len(parts) >= 4 and parts[0] == "devices" and parts[2] == "sensors" and parts[3] == "ctd"


def buoy_uuid_from_ctd_topic(topic: str) -> str | None:
    """Return the device UUID embedded in a CTD topic path."""
    if not is_ctd_topic(topic):
        return None
    return topic.split("/")[1]


def parse_ctd_payload(payload: bytes) -> ctd_pb2.CtdSensor:
    """Deserialize raw MQTT payload bytes into a CtdSensor protobuf message."""
    ctd = ctd_pb2.CtdSensor()
    try:
        ctd.ParseFromString(payload)
    except DecodeError as exc:
        raise CtdParseError(f"invalid CTD protobuf payload: {exc}") from exc
    return ctd


def extract_temperature(ctd: ctd_pb2.CtdSensor) -> float:
    """Return CTD temperature in degrees Celsius."""
    return float(ctd.temperature)
