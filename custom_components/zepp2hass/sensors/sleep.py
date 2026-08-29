"""Sleep sensor for Zepp2Hass.

Provides the sleep score and detailed attributes like sleep stages and naps.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.components.sensor import SensorStateClass

from .base import ZeppSensorBase
from ..const import DataSection

if TYPE_CHECKING:
    from ..coordinator import ZeppDataUpdateCoordinator


class SleepScoreSensor(ZeppSensorBase):
    """Sleep Score sensor with detailed stage attributes."""

    _SECTION = DataSection.SLEEP

    def __init__(self, coordinator: ZeppDataUpdateCoordinator) -> None:
        """Initialize the sleep score sensor."""
        super().__init__(
            coordinator=coordinator,
            key="sleep_score",
            name="Sleep Score",
            icon="mdi:sleep",
            unit="points",
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self._is_coordinator_ready():
            return False
        section = self._get_section(self._SECTION)
        return "info" in section and "score" in section["info"]

    @property
    def native_value(self) -> int | None:
        """Return the sleep score."""
        section = self._get_section(self._SECTION)
        return section.get("info", {}).get("score")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes including formatted sleep stages."""
        section = self._get_section(self._SECTION)
        if not section:
            return {}
        
        attributes = {}
        
        # Format sleep stages
        stg_list = section.get("stg_list", {})
        stages = section.get("stage", [])
        naps = section.get("nap", [])
        
        if stages and stg_list:
            # Create reverse mapping: {7: "WAKE_STAGE", 8: "REM_STAGE", ...}
            model_to_name = {v: k for k, v in stg_list.items()}
            
            from .formatters import format_sleep_time, format_timestamp_iso
            
            formatted_stages = []
            for stage in stages:
                model = stage.get("model")
                start = stage.get("start")
                stop = stage.get("stop")
                
                phase_name = model_to_name.get(model, f"UNKNOWN ({model})")
                
                # format_sleep_time returns a datetime object
                start_dt = format_sleep_time(start) if start is not None else None
                stop_dt = format_sleep_time(stop) if stop is not None else None
                
                duration_min = None
                if start is not None and stop is not None:
                    duration_min = stop - start if stop >= start else (1440 - start) + stop
                
                formatted_stages.append({
                    "phase": phase_name,
                    "start": start_dt.isoformat() if start_dt else None,
                    "stop": stop_dt.isoformat() if stop_dt else None,
                    "duration_min": duration_min,
                })
            
            attributes["stages"] = formatted_stages
            
        if naps:
            attributes["naps"] = naps
            
        return attributes
