"""Tests for CLI buoy selection."""

from __future__ import annotations

import pytest

from spear_mqtt_ctd.cli import main
from spear_mqtt_ctd.uuid import build_buoy_serial, serial_to_buoy_uuid


def _write_broker_config(path) -> None:
    path.write_text(
        """/**/*:
  ros__parameters:
    host: broker.example.com
    port: 8883
    user: test-user
    pass: test-pass
""",
        encoding="utf-8",
    )


def _patch_single_client_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    class StopOnSleepEvent:
        def __init__(self) -> None:
            self._stop = False

        def is_set(self) -> bool:
            return self._stop

        def set(self) -> None:
            self._stop = True

        def wait(self, _timeout: float | None = None) -> bool:
            return self._stop

    stop_event = StopOnSleepEvent()

    monkeypatch.setattr("spear_mqtt_ctd.cli.threading.Event", lambda: stop_event)
    monkeypatch.setattr("spear_mqtt_ctd.cli.time.sleep", lambda _sec: stop_event.set())
    monkeypatch.setattr("spear_mqtt_ctd.cli.CtdMqttClient.connect", lambda self: None)
    monkeypatch.setattr("spear_mqtt_ctd.cli.CtdMqttClient.start", lambda self: None)
    monkeypatch.setattr("spear_mqtt_ctd.cli.CtdMqttClient.stop", lambda self: None)
    monkeypatch.setattr("spear_mqtt_ctd.cli.start_heartbeat_thread", lambda *args, **kwargs: None)


def test_cli_missing_mode_non_interactive_returns_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": lambda self: False})())
    assert main(["--config", "unused.yaml"]) == 2


def test_cli_family_and_unit_runs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_file = tmp_path / "mqtt.yaml"
    _write_broker_config(config_file)
    _patch_single_client_lifecycle(monkeypatch)
    monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": lambda self: True})())

    assert (
        main(
            [
                "--config",
                str(config_file),
                "--family",
                "BEN",
                "--unit",
                "02",
            ]
        )
        == 0
    )


def test_cli_snapshot_flag_runs(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    config_file = tmp_path / "mqtt.yaml"
    _write_broker_config(config_file)

    def fake_snapshot(config_path, **kwargs):
        assert config_path == str(config_file)
        assert kwargs["wait_sec"] == 12.0
        return []

    monkeypatch.setattr("spear_mqtt_ctd.cli.run_fleet_snapshot", fake_snapshot)

    assert (
        main(
            [
                "--config",
                str(config_file),
                "--snapshot",
                "--snapshot-wait-sec",
                "12",
            ]
        )
        == 0
    )


def test_cli_snapshot_conflicts_with_serial(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_file = tmp_path / "mqtt.yaml"
    _write_broker_config(config_file)
    monkeypatch.setattr("sys.stdin", type("T", (), {"isatty": lambda self: False})())

    assert (
        main(
            [
                "--config",
                str(config_file),
                "--snapshot",
                "--serial",
                "MDA001-0000-00027",
            ]
        )
        == 2
    )


def test_cli_serial_matches_family_unit_shortcut() -> None:
    serial = build_buoy_serial("BEN", "02")
    assert serial == "BEN001-0000-00002"
    assert serial_to_buoy_uuid(serial) == serial_to_buoy_uuid("BEN001-0000-00002")
