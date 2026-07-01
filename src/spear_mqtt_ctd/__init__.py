"""Public API for spear-mqtt-ctd."""

from spear_mqtt_ctd.config import BrokerConfig, load_broker_config
from spear_mqtt_ctd.fleet import GUI_FLEET_SERIALS, gui_fleet_serials
from spear_mqtt_ctd.health import (
    DEFAULT_MAX_AGE_SEC,
    DEFAULT_MAX_STEP_C,
    MAX_PLAUSIBLE_TEMP_C,
    MIN_PLAUSIBLE_TEMP_C,
    PlausibilityResult,
    evaluate_temperature_plausibility,
    is_finite_temperature,
    is_in_seawater_range,
)
from spear_mqtt_ctd.mqtt_client import CtdMqttClient
from spear_mqtt_ctd.parser import (
    CTD_TOPIC_SUFFIX,
    CtdParseError,
    buoy_uuid_from_ctd_topic,
    extract_temperature,
    is_ctd_topic,
    parse_ctd_payload,
)
from spear_mqtt_ctd.snapshot import (
    DEFAULT_SNAPSHOT_WAIT_SEC,
    SnapshotRow,
    build_snapshot_rows,
    run_fleet_snapshot,
)
from spear_mqtt_ctd.uuid import (
    BuoySelection,
    MonitorMode,
    build_buoy_serial,
    prompt_buoy_serial,
    prompt_monitor_mode,
    resolve_buoy_selection,
    resolve_monitor_mode,
    serial_to_buoy_uuid,
)

__all__ = [
    "BrokerConfig",
    "BuoySelection",
    "CTD_TOPIC_SUFFIX",
    "CtdMqttClient",
    "CtdParseError",
    "DEFAULT_MAX_AGE_SEC",
    "DEFAULT_MAX_STEP_C",
    "DEFAULT_SNAPSHOT_WAIT_SEC",
    "GUI_FLEET_SERIALS",
    "MAX_PLAUSIBLE_TEMP_C",
    "MIN_PLAUSIBLE_TEMP_C",
    "MonitorMode",
    "PlausibilityResult",
    "SnapshotRow",
    "build_buoy_serial",
    "build_snapshot_rows",
    "buoy_uuid_from_ctd_topic",
    "evaluate_temperature_plausibility",
    "extract_temperature",
    "gui_fleet_serials",
    "is_ctd_topic",
    "is_finite_temperature",
    "is_in_seawater_range",
    "load_broker_config",
    "parse_ctd_payload",
    "prompt_buoy_serial",
    "prompt_monitor_mode",
    "resolve_buoy_selection",
    "resolve_monitor_mode",
    "run_fleet_snapshot",
    "serial_to_buoy_uuid",
]
