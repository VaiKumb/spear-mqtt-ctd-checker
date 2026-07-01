"""One-shot fleet-wide CTD status snapshot over MQTT."""

from __future__ import annotations

import math
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import certifi
import paho.mqtt.client as mqtt

from spear_mqtt_ctd.config import BrokerConfig, load_broker_config
from spear_mqtt_ctd.fleet import gui_fleet_serials
from spear_mqtt_ctd.health import (
    DEFAULT_MAX_AGE_SEC,
    DEFAULT_MAX_STEP_C,
    evaluate_temperature_plausibility,
)
from spear_mqtt_ctd.parser import (
    buoy_uuid_from_ctd_topic,
    extract_temperature,
    is_ctd_topic,
    parse_ctd_payload,
)
from spear_mqtt_ctd.status import ReadingStatus
from spear_mqtt_ctd.terminal import format_snapshot_table
from spear_mqtt_ctd.uuid import serial_to_buoy_uuid

CTD_TOPIC_WILDCARD = "devices/+/sensors/ctd"
DEFAULT_SNAPSHOT_WAIT_SEC = 15.0


@dataclass(frozen=True)
class SnapshotRow:
    serial: str
    buoy_uuid: str
    status: ReadingStatus | None = None


class CtdSnapshotCollector:
    """Collect latest CTD status per buoy UUID from a wildcard MQTT subscription."""

    def __init__(
        self,
        config_path: str,
        max_age_sec: float = DEFAULT_MAX_AGE_SEC,
        max_step_c: float = DEFAULT_MAX_STEP_C,
        broker_config: BrokerConfig | None = None,
    ) -> None:
        self._config = broker_config or load_broker_config(config_path)
        self._max_age_sec = max_age_sec
        self._max_step_c = max_step_c
        self._status_by_uuid: dict[str, ReadingStatus] = {}
        self._last_temperature_by_uuid: dict[str, float] = {}
        self._lock = threading.Lock()

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(self._config.user, self._config.password)
        self._client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=certifi.where(),
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def handle_message(self, topic: str, payload: bytes, now: datetime | None = None) -> bool:
        """Parse a CTD message and store the latest status for its buoy UUID."""
        if not is_ctd_topic(topic):
            return False

        buoy_uuid = buoy_uuid_from_ctd_topic(topic)
        if buoy_uuid is None:
            return False

        ctd = parse_ctd_payload(payload)
        temperature = extract_temperature(ctd)
        previous_temperature = self._last_temperature_by_uuid.get(buoy_uuid)
        result = evaluate_temperature_plausibility(
            temperature,
            stamp=ctd.stamp,
            now=now,
            max_age_sec=self._max_age_sec,
            previous_temperature=previous_temperature,
            max_step_c=self._max_step_c,
        )
        received_at = now or datetime.now(tz=UTC)
        status = ReadingStatus.from_result(temperature, result, received_at)

        with self._lock:
            self._status_by_uuid[buoy_uuid] = status
            if math.isfinite(temperature):
                self._last_temperature_by_uuid[buoy_uuid] = temperature

        return True

    def collect(self, wait_sec: float) -> dict[str, ReadingStatus]:
        """Subscribe to all CTD topics, collect readings for wait_sec, then disconnect."""
        self._status_by_uuid.clear()
        self._last_temperature_by_uuid.clear()

        loop_thread = threading.Thread(
            target=self._client.loop_forever,
            name="spear-mqtt-ctd-snapshot-loop",
            daemon=True,
        )
        self._client.connect(self._config.host, self._config.port)
        loop_thread.start()
        time.sleep(wait_sec)
        self._client.disconnect()
        loop_thread.join(timeout=5.0)

        with self._lock:
            return dict(self._status_by_uuid)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Any = None,
    ) -> None:
        if reason_code.is_failure:
            print(f"Failed to connect to MQTT broker, return code: {reason_code}")
            return
        client.subscribe(CTD_TOPIC_WILDCARD, qos=0)
        print(f"Collecting CTD readings from {CTD_TOPIC_WILDCARD} ...")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        self.handle_message(msg.topic, msg.payload)


def build_snapshot_rows(
    fleet_serials: list[str],
    status_by_uuid: dict[str, ReadingStatus],
) -> list[SnapshotRow]:
    """Build one row per fleet serial using collected UUID statuses."""
    return [
        SnapshotRow(
            serial=serial,
            buoy_uuid=serial_to_buoy_uuid(serial),
            status=status_by_uuid.get(serial_to_buoy_uuid(serial)),
        )
        for serial in fleet_serials
    ]


def run_fleet_snapshot(
    config_path: str,
    *,
    wait_sec: float = DEFAULT_SNAPSHOT_WAIT_SEC,
    max_age_sec: float = DEFAULT_MAX_AGE_SEC,
    max_step_c: float = DEFAULT_MAX_STEP_C,
    broker_config: BrokerConfig | None = None,
    fleet_serials: list[str] | None = None,
) -> list[SnapshotRow]:
    """Connect, collect CTD statuses for GUI fleet buoys, print a table, and return rows."""
    serials = fleet_serials if fleet_serials is not None else gui_fleet_serials()
    collector = CtdSnapshotCollector(
        config_path=config_path,
        max_age_sec=max_age_sec,
        max_step_c=max_step_c,
        broker_config=broker_config,
    )
    print(f"Snapshot window: {wait_sec:g}s ({len(serials)} GUI fleet buoys)")
    status_by_uuid = collector.collect(wait_sec)
    rows = build_snapshot_rows(serials, status_by_uuid)
    print(format_snapshot_table(rows))
    return rows
