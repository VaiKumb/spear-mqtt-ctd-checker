"""Tests for buoy serial to UUID conversion."""

from __future__ import annotations

import pytest

from spear_mqtt_ctd.uuid import (
    build_buoy_serial,
    prompt_buoy_serial,
    resolve_buoy_selection,
    resolve_monitor_mode,
    serial_to_buoy_uuid,
)


def test_serial_to_buoy_uuid_matches_edge_sensors_config() -> None:
    assert serial_to_buoy_uuid("MDA001-0000-00003") == "cedd2016-35c8-5941-8b28-365532372fa1"
    assert serial_to_buoy_uuid("MDA001-0000-00027") == "ba5d742f-b799-5462-ba42-7059d53e7840"


def test_serial_to_buoy_uuid_is_case_insensitive() -> None:
    assert serial_to_buoy_uuid("mda001-0000-00003") == serial_to_buoy_uuid("MDA001-0000-00003")


def test_doppleganger_serial() -> None:
    assert serial_to_buoy_uuid("doppleganger") == "b747311e-75f9-5968-8b45-bad23348c07f"
    assert serial_to_buoy_uuid("DOPPLEGANGER") == serial_to_buoy_uuid("doppleganger")


def test_build_buoy_serial_ben() -> None:
    assert build_buoy_serial("BEN", "02") == "BEN001-0000-00002"
    assert build_buoy_serial("ben", 2) == "BEN001-0000-00002"


def test_build_buoy_serial_mda() -> None:
    assert build_buoy_serial("MDA", "27") == "MDA001-0000-00027"


def test_build_buoy_serial_rejects_invalid_family() -> None:
    with pytest.raises(ValueError, match="family must be BEN or MDA"):
        build_buoy_serial("FOO", "02")


def test_build_buoy_serial_rejects_non_numeric_unit() -> None:
    with pytest.raises(ValueError, match="unit must be numeric"):
        build_buoy_serial("BEN", "abc")


def test_prompt_buoy_serial() -> None:
    inputs = iter(["ben", "02"])
    serial = prompt_buoy_serial(input_func=lambda _prompt: next(inputs), print_func=lambda *_args: None)
    assert serial == "BEN001-0000-00002"


def test_resolve_buoy_selection_from_serial() -> None:
    selection = resolve_buoy_selection(
        serial="MDA001-0000-00027",
        prompt_if_missing=False,
    )
    assert selection.serial == "MDA001-0000-00027"
    assert selection.buoy_uuid == serial_to_buoy_uuid("MDA001-0000-00027")


def test_resolve_buoy_selection_from_family_and_unit() -> None:
    selection = resolve_buoy_selection(
        family="MDA",
        unit="27",
        prompt_if_missing=False,
    )
    assert selection.serial == "MDA001-0000-00027"
    assert selection.buoy_uuid == serial_to_buoy_uuid("MDA001-0000-00027")


def test_resolve_buoy_selection_from_uuid() -> None:
    uuid = serial_to_buoy_uuid("MDA001-0000-00027")
    selection = resolve_buoy_selection(buoy_uuid=uuid, prompt_if_missing=False)
    assert selection.buoy_uuid == uuid
    assert selection.serial is None


def test_resolve_buoy_selection_rejects_mixed_args() -> None:
    with pytest.raises(ValueError, match="Use either --serial or --family/--unit"):
        resolve_buoy_selection(
            serial="MDA001-0000-00027",
            family="MDA",
            unit="27",
            prompt_if_missing=False,
        )


def test_resolve_buoy_selection_requires_family_and_unit_together() -> None:
    with pytest.raises(ValueError, match="must be used together"):
        resolve_buoy_selection(family="BEN", prompt_if_missing=False)


def test_resolve_monitor_mode_single_when_buoy_args_provided() -> None:
    assert (
        resolve_monitor_mode(single_buoy_requested=True, prompt_if_missing=False) == "single"
    )
