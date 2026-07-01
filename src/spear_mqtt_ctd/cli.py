"""Command-line entry point for the CTD MQTT checker."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time

from spear_mqtt_ctd.heartbeat import start_heartbeat_thread
from spear_mqtt_ctd.health import DEFAULT_MAX_AGE_SEC, DEFAULT_MAX_STEP_C
from spear_mqtt_ctd.mqtt_client import CtdMqttClient
from spear_mqtt_ctd.snapshot import DEFAULT_SNAPSHOT_WAIT_SEC, run_fleet_snapshot
from spear_mqtt_ctd.terminal import DEFAULT_HEARTBEAT_SEC, format_implausible, format_plausible
from spear_mqtt_ctd.uuid import (
    BuoySelection,
    MonitorMode,
    resolve_buoy_selection,
    resolve_monitor_mode,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Subscribe to CTD MQTT topics and validate temperature plausibility.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to Spear MQTT broker YAML config (e.g. ~/.ros/mqtt-broker-spear-hivemq.yaml)",
    )
    buoy_group = parser.add_mutually_exclusive_group(required=False)
    buoy_group.add_argument(
        "--buoy-uuid",
        help="Buoy UUID used in the MQTT topic devices/<uuid>/sensors/ctd",
    )
    buoy_group.add_argument(
        "--serial",
        "-s",
        help="Buoy serial number (e.g. MDA001-0000-00027); converted to MQTT UUID automatically",
    )
    parser.add_argument(
        "--family",
        choices=["BEN", "MDA", "ben", "mda"],
        help="Buoy family prefix; use with --unit (e.g. BEN + 02 -> BEN001-0000-00002)",
    )
    parser.add_argument(
        "--unit",
        help="Buoy unit number (e.g. 02, 27); use with --family",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Snapshot all GUI fleet buoys once and exit (no heartbeat loop)",
    )
    parser.add_argument(
        "--snapshot-wait-sec",
        type=float,
        default=DEFAULT_SNAPSHOT_WAIT_SEC,
        help=f"Seconds to collect MQTT readings in snapshot mode (default: {DEFAULT_SNAPSHOT_WAIT_SEC})",
    )
    parser.add_argument(
        "--max-age-sec",
        type=float,
        default=DEFAULT_MAX_AGE_SEC,
        help=f"Reject readings older than this many seconds (default: {DEFAULT_MAX_AGE_SEC})",
    )
    parser.add_argument(
        "--max-step-c",
        type=float,
        default=DEFAULT_MAX_STEP_C,
        help=(
            "Reject readings that jump more than this many degrees C from the prior "
            f"reading (default: {DEFAULT_MAX_STEP_C})"
        ),
    )
    parser.add_argument(
        "--heartbeat-sec",
        type=float,
        default=DEFAULT_HEARTBEAT_SEC,
        help=f"Print status every N seconds (default: {DEFAULT_HEARTBEAT_SEC}, 0 to disable)",
    )
    return parser


def _single_buoy_requested(args: argparse.Namespace) -> bool:
    return bool(args.buoy_uuid or args.serial or args.family or args.unit)


def _run_single_monitor(
    args: argparse.Namespace,
    selection: BuoySelection,
    stop_event: threading.Event,
) -> None:
    def on_plausible(temperature: float, _ctd) -> None:
        print(format_plausible(temperature))

    def on_implausible(temperature: float, reason: str, _ctd) -> None:
        print(format_implausible(temperature, reason))

    client = CtdMqttClient(
        config_path=args.config,
        buoy_uuid=selection.buoy_uuid,
        max_age_sec=args.max_age_sec,
        max_step_c=args.max_step_c,
        on_plausible=on_plausible,
        on_implausible=on_implausible,
    )

    print(f"Connecting to broker using config {args.config}")
    if selection.serial is not None:
        print(f"Buoy serial: {selection.serial} (UUID: {selection.buoy_uuid})")
    else:
        print(f"Buoy UUID: {selection.buoy_uuid}")
    print(
        f"Plausibility: seawater range, max age {args.max_age_sec}s, "
        f"max step {args.max_step_c} C"
    )
    if args.heartbeat_sec > 0:
        print(f"Status heartbeat every {args.heartbeat_sec:g}s")

    client.connect()
    client.start()

    if args.heartbeat_sec > 0:
        start_heartbeat_thread(client, stop_event, interval_sec=args.heartbeat_sec)

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    finally:
        stop_event.set()
        client.stop()


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    stop_event = threading.Event()

    def _handle_signal(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        mode: MonitorMode = resolve_monitor_mode(
            snapshot=args.snapshot,
            single_buoy_requested=_single_buoy_requested(args),
            prompt_if_missing=sys.stdin.isatty(),
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    if mode == "snapshot":
        print(f"Connecting to broker using config {args.config}")
        run_fleet_snapshot(
            args.config,
            wait_sec=args.snapshot_wait_sec,
            max_age_sec=args.max_age_sec,
            max_step_c=args.max_step_c,
        )
        return 0

    try:
        selection = resolve_buoy_selection(
            buoy_uuid=args.buoy_uuid,
            serial=args.serial,
            family=args.family,
            unit=args.unit,
            prompt_if_missing=sys.stdin.isatty(),
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    _run_single_monitor(args, selection, stop_event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
