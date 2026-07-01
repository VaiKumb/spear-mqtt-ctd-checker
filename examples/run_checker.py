#!/usr/bin/env python3
"""Minimal example: subscribe to CTD MQTT messages and check temperature plausibility."""

from __future__ import annotations

import threading

from spear_mqtt_ctd import CtdMqttClient
from spear_mqtt_ctd.heartbeat import start_heartbeat_thread
from spear_mqtt_ctd.snapshot import run_fleet_snapshot
from spear_mqtt_ctd.terminal import (
    DEFAULT_HEARTBEAT_SEC,
    format_implausible,
    format_plausible,
)
from spear_mqtt_ctd.uuid import resolve_buoy_selection, resolve_monitor_mode

DEFAULT_CONFIG_PATH = "~/.ros/mqtt-broker-spear-hivemq.yaml"


def main() -> None:
    mode = resolve_monitor_mode()
    if mode == "snapshot":
        run_fleet_snapshot(DEFAULT_CONFIG_PATH)
        return

    selection = resolve_buoy_selection()
    stop_event = threading.Event()
    client = CtdMqttClient(
        config_path=DEFAULT_CONFIG_PATH,
        buoy_uuid=selection.buoy_uuid,
        on_plausible=lambda temp, _ctd: print(format_plausible(temp)),
        on_implausible=lambda temp, reason, _ctd: print(format_implausible(temp, reason)),
    )
    client.connect()
    print(f"Buoy serial: {selection.serial} (UUID: {selection.buoy_uuid})")
    print(f"Listening on {client.ctd_topic} (Ctrl+C to stop)")
    print(f"Status heartbeat every {DEFAULT_HEARTBEAT_SEC:g}s")
    start_heartbeat_thread(client, stop_event, interval_sec=DEFAULT_HEARTBEAT_SEC)
    try:
        client.start_blocking()
    except KeyboardInterrupt:
        stop_event.set()
        client.stop()


if __name__ == "__main__":
    main()
