"""Fleet buoy serial list aligned with edge-sensors spear_gui dropdown."""

from __future__ import annotations

# Matches spear_gui/spear_gui/spear_gui.py::_buoy_strs
GUI_FLEET_SERIALS: tuple[str, ...] = (
    "doppleganger",
    "BEN001-0000-00001",
    "BEN001-0000-00002",
    "BEN001-0000-00003",
    "BEN001-0000-00010",
    "MDA001-0000-00000",
    "MDA001-0000-00001",
    "MDA001-0000-00002",
    "MDA001-0000-00003",
    "MDA001-0000-00004",
    "MDA001-0000-00005",
    "MDA001-0000-00006",
    "MDA001-0000-00007",
    "MDA001-0000-00008",
    "MDA001-0000-00009",
    "MDA001-0000-00010",
    "MDA001-0000-00011",
    "MDA001-0000-00012",
    "MDA001-0000-00013",
    "MDA001-0000-00014",
    "MDA001-0000-00015",
    "MDA001-0000-00016",
    "MDA001-0000-00017",
    "MDA001-0000-00018",
    "MDA001-0000-00019",
    "MDA001-0000-00020",
    "MDA001-0000-00021",
    "MDA001-0000-00022",
    "MDA001-0000-00023",
    "MDA001-0000-00024",
    "MDA001-0000-00025",
    "MDA001-0000-00026",
    "MDA001-0000-00027",
    "MDA001-0000-00028",
    "MDA001-0000-00029",
)


def gui_fleet_serials() -> list[str]:
    """Return buoy serials from the edge-sensors GUI dropdown."""
    return list(GUI_FLEET_SERIALS)
