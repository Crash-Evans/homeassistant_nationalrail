

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .config_flow import (
    CONF_AVOID,
    CONF_DESTINATIONS,
    CONF_MAX_CHANGES,
    CONF_MIN_INTERCHANGE_MINS,
    CONF_PLANNER_PROVIDER,
    CONF_STATION,
    CONF_TRANSPORTAPI_APP_ID,
    CONF_TRANSPORTAPI_APP_KEY,
    CONF_VIA,
)
from .planner.transportapi_client import TransportApiClient

_LOGGER = logging.getLogger(__name__)


class JourneyPlannerCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches planned itineraries (TransportAPI for now)."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="National Rail Journey Planner",
            update_interval=dt.timedelta(seconds=90),
        )
        self.entry = entry

        data = entry.data
        provider = data.get(CONF_PLANNER_PROVIDER, "transportapi")
        if provider != "transportapi":
            _LOGGER.warning(
                "Only 'transportapi' is implemented in this fork so far; got %s",
                provider,
            )
        app_id = data.get(CONF_TRANSPORTAPI_APP_ID)
        app_key = data.get(CONF_TRANSPORTAPI_APP_KEY)
        if not app_id or not app_key:
            _LOGGER.warning(
                "TransportAPI credentials are missing; planner will be disabled"
            )
        self._transport = (
            TransportApiClient(app_id, app_key) if app_id and app_key else None
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        data = self.entry.data
        origin: str = data.get(CONF_STATION)
        dests: List[str] = data.get(CONF_DESTINATIONS) or []
        destination: Optional[str] = dests[0] if dests else None
        if not origin or not destination:
            return {"itineraries": [], "error": "origin_or_destination_missing"}
        if not self._transport:
            return {"itineraries": [], "error": "transportapi_credentials_missing"}

        tz = self.hass.config.time_zone
        when = dt.datetime.now(dt.timezone.utc).astimezone() if tz else dt.datetime.now()

        payload = await self._transport.plan(
            origin=origin,
            destination=destination,
            when=when,
            via=data.get(CONF_VIA),
            avoid=data.get(CONF_AVOID),
            max_changes=int(data.get(CONF_MAX_CHANGES, 2)),
            min_interchange=int(data.get(CONF_MIN_INTERCHANGE_MINS, 5)),
        )
        itineraries = TransportApiClient.to_simple_itineraries(payload)

        # Keep only top 3 to avoid huge attributes
        itineraries = itineraries[:3]

        return {
            "origin": origin,
            "destination": destination,
            "via": data.get(CONF_VIA),
            "when": when.isoformat(),
            "itineraries": itineraries,
            # Toggle this by setting hass.data["_nr_debug_raw"] = True somewhere (dev use only)
            "raw": payload if self.hass.data.get("_nr_debug_raw") else None,
        }