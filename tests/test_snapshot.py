"""Tests for fleet CTD snapshot mode."""

from __future__ import annotations

from datetime import UTC, datetime

from spear_mqtt_ctd import ctd_pb2
from spear_mqtt_ctd.config import BrokerConfig
from spear_mqtt_ctd.fleet import gui_fleet_serials
from spear_mqtt_ctd.snapshot import (
    CtdSnapshotCollector,
    build_snapshot_rows,
    run_fleet_snapshot,
)
from spear_mqtt_ctd.terminal import format_snapshot_table
from spear_mqtt_ctd.uuid import prompt_monitor_mode, resolve_monitor_mode, serial_to_buoy_uuid


def _ctd_payload(temperature: float, when: datetime | None = None) -> bytes:
    ctd = ctd_pb2.CtdSensor()
    ctd.temperature = temperature
    if when is not None:
        ctd.stamp.FromDatetime(when)
    return ctd.SerializeToString()


def _make_collector() -> CtdSnapshotCollector:
    return CtdSnapshotCollector(
        config_path="unused",
        broker_config=BrokerConfig(
            host="example.com",
            port=8883,
            user="user",
            password="pass",
        ),
    )


def test_buoy_uuid_from_ctd_topic_via_handle_message() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    serial = "MDA001-0000-00027"
    buoy_uuid = serial_to_buoy_uuid(serial)
    payload = _ctd_payload(12.0, now)
    collector = _make_collector()

    assert collector.handle_message(f"devices/{buoy_uuid}/sensors/ctd", payload, now=now) is True

    status = collector._status_by_uuid[buoy_uuid]
    assert status.plausible is True
    assert status.temperature == 12.0


def test_build_snapshot_rows_marks_missing_buoys_as_no_data() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    serial = "BEN001-0000-00002"
    buoy_uuid = serial_to_buoy_uuid(serial)
    collector = _make_collector()
    collector.handle_message(
        f"devices/{buoy_uuid}/sensors/ctd",
        _ctd_payload(5.0, now),
        now=now,
    )

    rows = build_snapshot_rows(["BEN001-0000-00002", "MDA001-0000-00027"], collector._status_by_uuid)
    assert rows[0].status is not None
    assert rows[0].status.plausible is True
    assert rows[1].status is None


def test_format_snapshot_table_includes_counts_and_rows() -> None:
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    serial = "MDA001-0000-00003"
    buoy_uuid = serial_to_buoy_uuid(serial)
    collector = _make_collector()
    collector.handle_message(
        f"devices/{buoy_uuid}/sensors/ctd",
        _ctd_payload(87.0, now),
        now=now,
    )
    rows = build_snapshot_rows([serial, "BEN001-0000-00002"], collector._status_by_uuid)
    table = format_snapshot_table(rows)

    assert "1 buoy(s) with data, 1 with no data" in table
    assert "MDA001-0000-00003" in table
    assert "IMPLAUSIBLE (above_range)" in table
    assert "BEN001-0000-00002" in table
    assert "NO DATA" in table


def test_run_fleet_snapshot_uses_gui_fleet_and_mock_collect(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect(self, wait_sec: float):
        captured["wait_sec"] = wait_sec
        return {}

    monkeypatch.setattr(CtdSnapshotCollector, "collect", fake_collect)

    rows = run_fleet_snapshot(
        "unused.yaml",
        wait_sec=7.5,
        fleet_serials=gui_fleet_serials(),
        broker_config=BrokerConfig("example.com", 8883, "user", "pass"),
    )
    assert captured["wait_sec"] == 7.5
    assert len(rows) == 35
    assert rows[0].serial == "doppleganger"


def test_prompt_monitor_mode() -> None:
    inputs = iter(["2"])
    mode = prompt_monitor_mode(input_func=lambda _prompt: next(inputs), print_func=lambda *_args: None)
    assert mode == "snapshot"


def test_resolve_monitor_mode_snapshot_flag() -> None:
    assert resolve_monitor_mode(snapshot=True, prompt_if_missing=False) == "snapshot"


def test_resolve_monitor_mode_rejects_snapshot_with_single_buoy() -> None:
    try:
        resolve_monitor_mode(snapshot=True, single_buoy_requested=True, prompt_if_missing=False)
    except ValueError as exc:
        assert "not both" in str(exc)
    else:
        raise AssertionError("expected ValueError")
