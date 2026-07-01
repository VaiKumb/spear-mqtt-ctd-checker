"""Periodic status heartbeat for long-running CTD checks."""

from __future__ import annotations

import threading

from spear_mqtt_ctd.mqtt_client import CtdMqttClient
from spear_mqtt_ctd.terminal import (
    DEFAULT_HEARTBEAT_SEC,
    format_implausible,
    format_plausible,
    format_waiting,
)


def print_reading_status(client: CtdMqttClient) -> None:
    """Print the latest CTD status line with color."""
    status = client.last_status
    if status is None:
        print(format_waiting())
        return

    if status.plausible:
        print(format_plausible(status.temperature))
    else:
        print(format_implausible(status.temperature, status.reason or "unknown"))


def heartbeat_loop(
    client: CtdMqttClient,
    stop_event: threading.Event,
    interval_sec: float = DEFAULT_HEARTBEAT_SEC,
) -> None:
    """Print status every interval_sec until stop_event is set."""
    while not stop_event.wait(interval_sec):
        print_reading_status(client)


def start_heartbeat_thread(
    client: CtdMqttClient,
    stop_event: threading.Event,
    interval_sec: float = DEFAULT_HEARTBEAT_SEC,
) -> threading.Thread:
    """Start a daemon thread that prints periodic status updates."""
    thread = threading.Thread(
        target=heartbeat_loop,
        args=(client, stop_event, interval_sec),
        name="spear-mqtt-ctd-heartbeat",
        daemon=True,
    )
    thread.start()
    return thread
