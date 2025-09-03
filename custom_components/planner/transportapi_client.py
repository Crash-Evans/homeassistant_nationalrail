from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .journey_coordinator import JourneyPlannerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = ["sensor"]


data_key = DOMAIN  # shorthand


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up via YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up National Rail UK from a config entry."""
    coordinator = JourneyPlannerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(data_key, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(data_key, {}).pop(entry.entry_id, None)
    return unload_ok