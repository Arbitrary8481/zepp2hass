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


def get_sleep_stage_duration(section: dict[str, Any], target_stage_name: str) -> int | None:
    """Calculate total minutes for a specific sleep stage name."""
    if not section:
        return None
    
    info = section.get("info", {})
    key_map = {
        "REM_STAGE": ["remTime", "rem_time", "rem"],
        "LIGHT_STAGE": ["lightTime", "light_time", "light", "shallowTime"],
        "WAKE_STAGE": ["wakeTime", "wake_time", "wake", "awakeTime"],
        "DEEP_STAGE": ["deepTime", "deep_time", "deep"],
    }
    
    for key in key_map.get(target_stage_name, []):
        if key in info and info[key] is not None:
            return info[key]
            
    # Calculate dynamically from sleep.stage and stg_list if not present in info
    stg_list = section.get("stg_list", {})
    stages = section.get("stage", [])
    
    if not stages or not stg_list:
        return 0
        
    target_model_id = stg_list.get(target_stage_name)
    if target_model_id is None:
        return 0
        
    total_minutes = 0
    for stage in stages:
        if stage.get("model") == target_model_id:
            start = stage.get("start")
            stop = stage.get("stop")
            if start is not None and stop is not None:
                duration = stop - start if stop >= start else (1440 - start) + stop
                total_minutes += duration
                
    return total_minutes


from homeassistant.components.sensor import SensorDeviceClass

class SleepStageDurationSensor(ZeppSensorBase):
    """Sensor for specific sleep stage duration (REM, Light, Wake, Deep)."""

    _SECTION = DataSection.SLEEP

    def __init__(
        self,
        coordinator: ZeppDataUpdateCoordinator,
        key: str,
        name: str,
        stage_name: str,
        icon: str,
    ) -> None:
        """Initialize sleep stage duration sensor."""
        super().__init__(
            coordinator=coordinator,
            key=key,
            name=name,
            icon=icon,
            unit="min",
        )
        self._stage_name = stage_name
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Return True if coordinator is ready and sleep section exists."""
        if not self._is_coordinator_ready():
            return False
        section = self._get_section(self._SECTION)
        return bool(section and ("info" in section or "stage" in section))

    @property
    def native_value(self) -> int | None:
        """Calculate and return duration in minutes."""
        section = self._get_section(self._SECTION)
        return get_sleep_stage_duration(section, self._stage_name)

