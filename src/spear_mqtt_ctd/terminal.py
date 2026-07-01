"""Colored terminal output for CTD plausibility status."""

from __future__ import annotations

import math

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

DEFAULT_HEARTBEAT_SEC = 30.0


def format_temperature(temperature: float) -> str:
    if math.isfinite(temperature):
        return f"{temperature:.3f} C"
    return str(temperature)


def format_plausible(temperature: float) -> str:
    return f"{GREEN}PLAUSIBLE: {format_temperature(temperature)}{RESET}"


def format_implausible(temperature: float, reason: str) -> str:
    return f"{RED}IMPLAUSIBLE ({reason}): {format_temperature(temperature)}{RESET}"


def format_waiting() -> str:
    return f"{YELLOW}WAITING: no CTD readings yet{RESET}"


def format_snapshot_status_label(status) -> str:
    """Plain-text status label for snapshot table rows."""
    if status is None:
        return "NO DATA"
    if status.plausible:
        return "PLAUSIBLE"
    return f"IMPLAUSIBLE ({status.reason or 'unknown'})"


def format_snapshot_table(rows) -> str:
    """Return a one-shot table of buoy CTD statuses."""
    active_rows = [row for row in rows if row.status is not None]
    inactive_count = len(rows) - len(active_rows)
    lines = [
        "",
        f"Snapshot results: {len(active_rows)} buoy(s) with data, {inactive_count} with no data",
        f"{'SERIAL':<22} {'STATUS':<28} {'TEMP':>12}",
        "-" * 64,
    ]
    for row in rows:
        if row.status is None:
            lines.append(f"{row.serial:<22} {'NO DATA':<28} {'-':>12}")
            continue
        label = format_snapshot_status_label(row.status)
        temp = format_temperature(row.status.temperature)
        lines.append(f"{row.serial:<22} {label:<28} {temp:>12}")
    return "\n".join(lines)
