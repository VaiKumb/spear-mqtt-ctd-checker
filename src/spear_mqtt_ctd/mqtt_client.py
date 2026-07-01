"""MQTT client that subscribes to CTD topics and checks temperature plausibility."""

from __future__ import annotations

import math
import ssl
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import certifi
import paho.mqtt.client as mqtt

from spear_mqtt_ctd.config import BrokerConfig, load_broker_config
from spear_mqtt_ctd.health import (
    DEFAULT_MAX_AGE_SEC,
    DEFAULT_MAX_STEP_C,
    PlausibilityResult,
    evaluate_temperature_plausibility,
)
from spear_mqtt_ctd.parser import extract_temperature, is_ctd_topic, parse_ctd_payload
from spear_mqtt_ctd.status import ReadingStatus


class CtdMqttClient:
    """Connect to the Spear MQTT broker and evaluate CTD temperature plausibility."""

    def __init__(
        self,
        config_path: str,
        buoy_uuid: str,
        max_age_sec: float = DEFAULT_MAX_AGE_SEC,
        max_step_c: float = DEFAULT_MAX_STEP_C,
        on_plausible: Callable[[float, Any], None] | None = None,
        on_implausible: Callable[[float, str, Any], None] | None = None,
        broker_config: BrokerConfig | None = None,
        # Deprecated aliases for earlier callback names.
        on_target_match: Callable[[float, Any], None] | None = None,
        on_ctd_reading: Callable[[float, Any], None] | None = None,
    ) -> None:
        self._config = broker_config or load_broker_config(config_path)
        self._buoy_uuid = buoy_uuid
        self._max_age_sec = max_age_sec
        self._max_step_c = max_step_c
        self._on_plausible = on_plausible or on_target_match
        self._on_implausible = on_implausible
        self._legacy_on_implausible = on_ctd_reading

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(self._config.user, self._config.password)
        self._client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=certifi.where(),
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._thread: threading.Thread | None = None
        self._connected = False
        self._last_plausible: bool | None = None
        self._last_temperature: float | None = None
        self._last_status: ReadingStatus | None = None

    @property
    def last_status(self) -> ReadingStatus | None:
        return self._last_status

    @property
    def ctd_topic(self) -> str:
        return f"devices/{self._buoy_uuid}/sensors/ctd"

    def connect(self) -> None:
        """Connect to the MQTT broker."""
        if self._client.is_connected():
            self._client.disconnect()
        self._client.connect(self._config.host, self._config.port)

    def start(self) -> None:
        """Start the blocking MQTT event loop on a background thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._client.loop_forever,
            name="spear-mqtt-ctd-loop",
            daemon=True,
        )
        self._thread.start()

    def start_blocking(self) -> None:
        """Run the MQTT event loop on the current thread until disconnected."""
        self._client.loop_forever()

    def stop(self) -> None:
        """Disconnect from the broker and stop the background loop."""
        self._client.disconnect()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    def evaluate_reading(self, ctd: Any, now: datetime | None = None) -> PlausibilityResult:
        """Evaluate plausibility for a parsed CTD message."""
        temperature = extract_temperature(ctd)
        return evaluate_temperature_plausibility(
            temperature,
            stamp=ctd.stamp,
            now=now,
            max_age_sec=self._max_age_sec,
            previous_temperature=self._last_temperature,
            max_step_c=self._max_step_c,
        )

    def handle_message(self, topic: str, payload: bytes, now: datetime | None = None) -> bool:
        """Parse a CTD message and invoke callbacks on plausibility state changes."""
        if not is_ctd_topic(topic):
            return False

        ctd = parse_ctd_payload(payload)
        temperature = extract_temperature(ctd)
        result = self.evaluate_reading(ctd, now=now)
        received_at = now or datetime.now(tz=UTC)
        self._last_status = ReadingStatus.from_result(temperature, result, received_at)

        state_changed = self._last_plausible is None or result.plausible != self._last_plausible
        if state_changed:
            self._last_plausible = result.plausible
            if result.plausible:
                if self._on_plausible is not None:
                    self._on_plausible(temperature, ctd)
            else:
                reason = result.reason or "unknown"
                if self._on_implausible is not None:
                    self._on_implausible(temperature, reason, ctd)
                elif self._legacy_on_implausible is not None:
                    self._legacy_on_implausible(temperature, ctd)

        if math.isfinite(temperature):
            self._last_temperature = temperature

        return True

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

        client.subscribe(self.ctd_topic, qos=0)
        self._connected = True
        print(f"Subscribed to {self.ctd_topic}")

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: mqtt.DisconnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Any = None,
    ) -> None:
        self._connected = False
        print("MQTT client disconnected")

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        self.handle_message(msg.topic, msg.payload)
