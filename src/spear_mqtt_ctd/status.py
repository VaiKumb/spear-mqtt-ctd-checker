"""Latest CTD reading status tracked by the MQTT client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from spear_mqtt_ctd.health import PlausibilityResult


@dataclass(frozen=True)
class ReadingStatus:
    temperature: float
    plausible: bool
    reason: str | None
    received_at: datetime

    @classmethod
    def from_result(
        cls,
        temperature: float,
        result: PlausibilityResult,
        received_at: datetime,
    ) -> ReadingStatus:
        return cls(
            temperature=temperature,
            plausible=result.plausible,
            reason=result.reason,
            received_at=received_at,
        )
