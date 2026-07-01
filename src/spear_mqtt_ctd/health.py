"""CTD temperature plausibility checks (aligned with edge-sensors atlas_ct seawater range)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

# TEOS-10 seawater range used by atlas_ct/i2c_ctd.py, slightly expanded.
MIN_PLAUSIBLE_TEMP_C = -6.0
MAX_PLAUSIBLE_TEMP_C = 45.0

DEFAULT_MAX_AGE_SEC = 60.0
DEFAULT_MAX_STEP_C = 2.0


@dataclass(frozen=True)
class PlausibilityResult:
    plausible: bool
    reason: str | None = None


def is_finite_temperature(temperature: float) -> bool:
    return math.isfinite(temperature)


def is_in_seawater_range(temperature: float) -> bool:
    return MIN_PLAUSIBLE_TEMP_C < temperature < MAX_PLAUSIBLE_TEMP_C


def _stamp_datetime(stamp: Any) -> datetime | None:
    if stamp is None:
        return None
    seconds = int(getattr(stamp, "seconds", 0))
    nanos = int(getattr(stamp, "nanos", 0))
    if seconds == 0 and nanos == 0:
        return None
    return datetime.fromtimestamp(seconds + nanos * 1e-9, tz=UTC)


def evaluate_temperature_plausibility(
    temperature: float,
    *,
    stamp: Any = None,
    now: datetime | None = None,
    max_age_sec: float = DEFAULT_MAX_AGE_SEC,
    previous_temperature: float | None = None,
    max_step_c: float = DEFAULT_MAX_STEP_C,
) -> PlausibilityResult:
    """Return whether a CTD temperature reading is plausible and why if not."""
    if not is_finite_temperature(temperature):
        return PlausibilityResult(False, "not_finite")

    if temperature <= MIN_PLAUSIBLE_TEMP_C:
        return PlausibilityResult(False, "below_range")

    if temperature >= MAX_PLAUSIBLE_TEMP_C:
        return PlausibilityResult(False, "above_range")

    reading_time = _stamp_datetime(stamp)
    if reading_time is not None:
        reference = now or datetime.now(tz=UTC)
        age_sec = (reference - reading_time).total_seconds()
        if age_sec > max_age_sec:
            return PlausibilityResult(False, "stale")

    if previous_temperature is not None and is_finite_temperature(previous_temperature):
        if abs(temperature - previous_temperature) > max_step_c:
            return PlausibilityResult(False, "unstable")

    return PlausibilityResult(True)
