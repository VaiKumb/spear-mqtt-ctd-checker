"""Tests for GUI fleet buoy list."""

from __future__ import annotations

from spear_mqtt_ctd.fleet import GUI_FLEET_SERIALS, gui_fleet_serials


def test_gui_fleet_serial_count_matches_edge_sensors_dropdown() -> None:
    assert len(GUI_FLEET_SERIALS) == 35


def test_gui_fleet_serials_include_known_buoys() -> None:
    serials = gui_fleet_serials()
    assert "doppleganger" in serials
    assert "BEN001-0000-00002" in serials
    assert "MDA001-0000-00027" in serials


def test_gui_fleet_serials_order_matches_edge_sensors_dropdown() -> None:
    assert gui_fleet_serials()[0] == "doppleganger"
    assert gui_fleet_serials()[1] == "BEN001-0000-00001"
    assert gui_fleet_serials()[-1] == "MDA001-0000-00029"
