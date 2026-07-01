"""Tests for CTD temperature plausibility checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from spear_mqtt_ctd import ctd_pb2
from spear_mqtt_ctd.health import (
    DEFAULT_MAX_STEP_C,
    MAX_PLAUSIBLE_TEMP_C,
    MIN_PLAUSIBLE_TEMP_C,
    PlausibilityResult,
    evaluate_temperature_plausibility,
    is_finite_temperature,
    is_in_seawater_range,
)


def _stamp_at(when: datetime):
    stamp = ctd_pb2.CtdSensor().stamp
    stamp.FromDatetime(when)
    return stamp


def test_finite_temperature() -> None:
    assert is_finite_temperature(12.3)
    assert not is_finite_temperature(float("nan"))
    assert not is_finite_temperature(float("inf"))


def test_seawater_range() -> None:
    assert is_in_seawater_range(0.0)
    assert is_in_seawater_range(MIN_PLAUSIBLE_TEMP_C + 0.1)
    assert is_in_seawater_range(MAX_PLAUSIBLE_TEMP_C - 0.1)
    assert not is_in_seawater_range(MIN_PLAUSIBLE_TEMP_C)
    assert not is_in_seawater_range(MAX_PLAUSIBLE_TEMP_C)
    assert not is_in_seawater_range(100.0)
    assert not is_in_seawater_range(-10000.0)


def test_plausible_reading() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    result = evaluate_temperature_plausibility(
        12.3,
        stamp=_stamp_at(now),
        now=now,
    )
    assert result == PlausibilityResult(True)


def test_arbitrary_five_is_plausible_not_special() -> None:
    result = evaluate_temperature_plausibility(5.0)
    assert result.plausible


def test_not_finite() -> None:
    result = evaluate_temperature_plausibility(float("nan"))
    assert result == PlausibilityResult(False, "not_finite")


def test_above_range() -> None:
    result = evaluate_temperature_plausibility(87.2)
    assert result == PlausibilityResult(False, "above_range")


def test_below_range() -> None:
    result = evaluate_temperature_plausibility(-10000.0)
    assert result == PlausibilityResult(False, "below_range")


def test_stale_reading() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    old = now - timedelta(seconds=120)
    result = evaluate_temperature_plausibility(
        12.3,
        stamp=_stamp_at(old),
        now=now,
        max_age_sec=60.0,
    )
    assert result == PlausibilityResult(False, "stale")


def test_missing_stamp_skips_freshness_check() -> None:
    result = evaluate_temperature_plausibility(12.3, stamp=None)
    assert result.plausible


def test_unstable_jump() -> None:
    result = evaluate_temperature_plausibility(
        15.0,
        previous_temperature=5.0,
        max_step_c=DEFAULT_MAX_STEP_C,
    )
    assert result == PlausibilityResult(False, "unstable")


def test_first_reading_skips_stability_check() -> None:
    result = evaluate_temperature_plausibility(
        15.0,
        previous_temperature=None,
        max_step_c=DEFAULT_MAX_STEP_C,
    )
    assert result.plausible


def test_stable_sequence() -> None:
    first = evaluate_temperature_plausibility(5.0)
    second = evaluate_temperature_plausibility(
        5.01,
        previous_temperature=5.0,
        max_step_c=0.1,
    )
    assert first.plausible
    assert second.plausible
