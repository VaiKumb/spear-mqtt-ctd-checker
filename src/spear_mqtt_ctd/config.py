"""Load Spear MQTT broker configuration from YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BrokerConfig:
    host: str
    port: int
    user: str
    password: str


def _extract_ros_parameters(document: dict[str, Any]) -> dict[str, Any]:
    """Extract ros__parameters from the nested YAML shape used by edge-sensors."""
    return next(iter(next(iter(document.values())).values()))


def load_broker_config(config_path: str | Path) -> BrokerConfig:
    """Load broker host, port, user, and pass from a Spear MQTT YAML config file."""
    path = Path(config_path).expanduser()
    with path.open("r", encoding="utf-8") as handle:
        document = yaml.load(handle, Loader=yaml.FullLoader)

    params = _extract_ros_parameters(document)
    return BrokerConfig(
        host=params["host"],
        port=int(params["port"]),
        user=params["user"],
        password=params["pass"],
    )
