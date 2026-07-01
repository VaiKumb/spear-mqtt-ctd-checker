"""Convert buoy serial numbers to MQTT topic UUIDs (same algorithm as edge-sensors)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

_SPEAR_UUID_NAMESPACE = uuid.UUID("13db1bb5-27ac-4bf7-8186-1043347c4247")

VALID_BUOY_FAMILIES = frozenset({"BEN", "MDA"})

MonitorMode = Literal["single", "snapshot"]


@dataclass(frozen=True)
class BuoySelection:
    """Resolved buoy identity for MQTT subscription."""

    buoy_uuid: str
    serial: str | None = None


def build_buoy_serial(family: str, unit: str | int) -> str:
    """Build a full buoy serial from family (BEN/MDA) and unit digits.

    Example: build_buoy_serial("BEN", "02") -> "BEN001-0000-00002"
    """
    family_upper = family.strip().upper()
    if family_upper not in VALID_BUOY_FAMILIES:
        raise ValueError(f"family must be BEN or MDA, got {family!r}")

    unit_str = str(unit).strip()
    if not unit_str.isdigit():
        raise ValueError(f"unit must be numeric, got {unit!r}")

    suffix = int(unit_str)
    if suffix < 0 or suffix > 99999:
        raise ValueError(f"unit must be between 0 and 99999, got {suffix}")

    return f"{family_upper}001-0000-{suffix:05d}"


def prompt_monitor_mode(
    *,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> MonitorMode:
    """Ask whether to monitor one buoy or run a fleet snapshot."""
    print_func("Select mode:")
    print_func("  1) Monitor one buoy (live updates + heartbeat)")
    print_func("  2) Snapshot all buoys (one-time status list)")
    while True:
        choice = input_func("Choice (1/2): ").strip()
        if choice == "1":
            return "single"
        if choice == "2":
            return "snapshot"
        print_func("Enter 1 or 2.")


def resolve_monitor_mode(
    *,
    snapshot: bool = False,
    single_buoy_requested: bool = False,
    prompt_if_missing: bool = True,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> MonitorMode:
    """Resolve monitor vs snapshot mode from flags or an interactive prompt."""
    if snapshot and single_buoy_requested:
        raise ValueError("Use either snapshot mode or single-buoy options, not both")
    if snapshot:
        return "snapshot"
    if single_buoy_requested:
        return "single"
    if prompt_if_missing:
        return prompt_monitor_mode(input_func=input_func, print_func=print_func)
    raise ValueError("Specify snapshot mode, single-buoy options, or run interactively")


def prompt_buoy_serial(
    *,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> str:
    """Interactively ask for buoy family and unit number."""
    print_func("Select buoy:")
    while True:
        family = input_func("Family (BEN/MDA): ").strip()
        if family.upper() in VALID_BUOY_FAMILIES:
            break
        print_func("Enter BEN or MDA.")

    while True:
        unit = input_func("Unit number (e.g. 02): ").strip()
        try:
            return build_buoy_serial(family, unit)
        except ValueError as exc:
            print_func(exc)


def resolve_buoy_selection(
    *,
    buoy_uuid: str | None = None,
    serial: str | None = None,
    family: str | None = None,
    unit: str | None = None,
    prompt_if_missing: bool = True,
    input_func: Callable[[str], str] = input,
    print_func: Callable[..., None] = print,
) -> BuoySelection:
    """Resolve buoy UUID from explicit args or an interactive prompt."""
    if buoy_uuid is not None:
        if serial is not None or family is not None or unit is not None:
            raise ValueError("Use only one of --buoy-uuid, --serial, or --family/--unit")
        return BuoySelection(buoy_uuid=buoy_uuid)

    if serial is not None:
        if family is not None or unit is not None:
            raise ValueError("Use either --serial or --family/--unit, not both")
        return BuoySelection(buoy_uuid=serial_to_buoy_uuid(serial), serial=serial)

    if family is not None or unit is not None:
        if family is None or unit is None:
            raise ValueError("--family and --unit must be used together")
        built_serial = build_buoy_serial(family, unit)
        return BuoySelection(
            buoy_uuid=serial_to_buoy_uuid(built_serial),
            serial=built_serial,
        )

    if prompt_if_missing:
        built_serial = prompt_buoy_serial(input_func=input_func, print_func=print_func)
        return BuoySelection(
            buoy_uuid=serial_to_buoy_uuid(built_serial),
            serial=built_serial,
        )

    raise ValueError(
        "Specify --buoy-uuid, --serial, or --family/--unit, or run interactively"
    )


def serial_to_buoy_uuid(serial: str) -> str:
    """Return the MQTT device UUID for a buoy serial (e.g. MDA001-0000-00027)."""
    if serial.lower() == "doppleganger":
        key = "doppleganger"
    else:
        key = serial.upper()
    return str(uuid.uuid5(_SPEAR_UUID_NAMESPACE, key))
