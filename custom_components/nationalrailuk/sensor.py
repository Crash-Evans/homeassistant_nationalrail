from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DESTINATIONS,
    CONF_STATION,
    CONF_VIA,
    DOMAIN,
)
from .journey_coordinator import JourneyPlannerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up journey planner sensors from a config entry."""
    coordinator: JourneyPlannerCoordinator = hass.data[DOMAIN][entry.entry_id]

    origin = entry.data.get(CONF_STATION, "?")
    dests = entry.data.get(CONF_DESTINATIONS, []) or []
    dest = dests[0] if dests else "?"
    via = entry.data.get(CONF_VIA)

    entities: list[SensorEntity] = [
        NextJourneySensor(coordinator, origin, dest, via, entry.entry_id),
        ItinerariesSensor(coordinator, origin, dest, via, entry.entry_id),
    ]
    async_add_entities(entities)


class _BaseJourneySensor(CoordinatorEntity[JourneyPlannerCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: JourneyPlannerCoordinator,
        origin: str,
        dest: str,
        via: Optional[str],
        entry_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._origin = origin
        self._dest = dest
        self._via = via
        self._entry_id = entry_id

    @property
    def device_info(self) -> Dict[str, Any]:
        name = f"{self._origin} → {self._dest}" + (f" via {self._via}" if self._via else "")
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": f"National Rail ({name})",
            "manufacturer": "National Rail / TransportAPI",
            "model": "Journey Planner",
        }


class NextJourneySensor(_BaseJourneySensor):
    _attr_icon = "mdi:train"

    @property
    def name(self) -> str:
        via = f" via {self._via}" if self._via else ""
        return f"Next journey {self._origin} → {self._dest}{via}"

    @property
    def unique_id(self) -> str:
        via = self._via or ""
        return f"{self._entry_id}_next_{self._origin}_{self._dest}_{via}"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        itins = data.get("itineraries") or []
        if not itins:
            return None
        first = itins[0]
        dep = first.get("departure_time")
        arr = first.get("arrival_time")
        if dep and arr:
            return f"{dep} → {arr}"
        return dep or arr

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        itins = data.get("itineraries") or []
        if not itins:
            return {
                "origin": self._origin,
                "destination": self._dest,
                "via": self._via,
                "itineraries": [],
            }
        first = itins[0]
        return {
            "origin": self._origin,
            "destination": self._dest,
            "via": self._via,
            "duration": first.get("duration"),
            "changes": first.get("changes"),
            "legs": first.get("legs"),
            "when": (self.coordinator.data or {}).get("when"),
        }


class ItinerariesSensor(_BaseJourneySensor):
    _attr_icon = "mdi:format-list-bulleted"

    @property
    def name(self) -> str:
        via = f" via {self._via}" if self._via else ""
        return f"Itineraries {self._origin} → {self._dest}{via}"

    @property
    def unique_id(self) -> str:
        via = self._via or ""
        return f"{self._entry_id}_itins_{self._origin}_{self._dest}_{via}"

    @property
    def native_value(self) -> int | None:
        itins = (self.coordinator.data or {}).get("itineraries") or []
        return len(itins) if itins is not None else None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "origin": self._origin,
            "destination": self._dest,
            "via": self._via,
            "itineraries": data.get("itineraries") or [],
            "when": data.get("when"),
        }
