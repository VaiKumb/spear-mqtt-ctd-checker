"""Tests for broker config loading."""

from __future__ import annotations

from pathlib import Path

from spear_mqtt_ctd.config import load_broker_config


def test_load_broker_config(tmp_path: Path) -> None:
    config_file = tmp_path / "mqtt.yaml"
    config_file.write_text(
        """/**/*:
  ros__parameters:
    host: broker.example.com
    port: 8883
    user: test-user
    pass: test-pass
""",
        encoding="utf-8",
    )

    config = load_broker_config(config_file)
    assert config.host == "broker.example.com"
    assert config.port == 8883
    assert config.user == "test-user"
    assert config.password == "test-pass"
