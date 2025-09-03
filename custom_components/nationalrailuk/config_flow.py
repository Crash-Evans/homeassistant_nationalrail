"""Config flow for National Rail UK integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import selector

from .client import (
    NationalRailClient,
    NationalRailClientInvalidInput,
    NationalRailClientInvalidToken,
)
from .const import (
    CONF_DESTINATIONS,
    CONF_STATION,
    CONF_TOKEN,
    DOMAIN,
    NATIONAL_RAIL_DATA_CLIENT,
)

from .crs import CRS

# Journey planner additions (local keys for now)
CONF_VIA = "via"
CONF_AVOID = "avoid"
CONF_MAX_CHANGES = "max_changes"
CONF_MIN_INTERCHANGE_MINS = "min_interchange_mins"
CONF_PLANNER_PROVIDER = "planner_provider"
CONF_TRANSPORTAPI_APP_ID = "transportapi_app_id"
CONF_TRANSPORTAPI_APP_KEY = "transportapi_app_key"

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_STATION): selector(
            {"select": {"options": CRS, "custom_value": True}}
        ),
        vol.Optional(CONF_DESTINATIONS): selector(
            {"select": {"options": CRS, "multiple": True, "custom_value": True}}
        ),
        # Journey planner options
        vol.Optional(CONF_VIA): selector(
            {"select": {"options": CRS, "custom_value": True}}
        ),
        vol.Optional(CONF_AVOID): selector(
            {"select": {"options": CRS, "custom_value": True}}
        ),
        vol.Optional(CONF_MAX_CHANGES, default=2): int,
        vol.Optional(CONF_MIN_INTERCHANGE_MINS, default=5): int,
        vol.Optional(CONF_PLANNER_PROVIDER, default="transportapi"): selector(
            {"select": {"options": ["transportapi", "ojp"], "custom_value": False}}
        ),
        vol.Optional(CONF_TRANSPORTAPI_APP_ID): str,
        vol.Optional(CONF_TRANSPORTAPI_APP_KEY): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # validate the token by calling a known line
    if DOMAIN not in hass.data:
        hass.data.setdefault(DOMAIN, {})

    if NATIONAL_RAIL_DATA_CLIENT not in hass.data[DOMAIN]:
        hass.data[DOMAIN][NATIONAL_RAIL_DATA_CLIENT] = NationalRailClient(hass)

    my_api: NationalRailClient = hass.data[DOMAIN][NATIONAL_RAIL_DATA_CLIENT]
    await my_api.set_header(data[CONF_TOKEN])

    try:
        # my_api = NationalRailClient(data[CONF_TOKEN], "STP", ["ZFD"], apiTest=True)

        res = await my_api.async_get_data("STP", ["ZFD"], apitest=True)
    except NationalRailClientInvalidToken as err:
        _LOGGER.exception(err)
        raise InvalidToken() from err

    # validate station input
    station = str(data[CONF_STATION]).strip().upper()
    dests_raw = data.get(CONF_DESTINATIONS) or []
    destinations = [str(d).strip().upper() for d in dests_raw]

    data[CONF_STATION] = station
    data[CONF_DESTINATIONS] = destinations

    if data.get(CONF_VIA):
        data[CONF_VIA] = str(data[CONF_VIA]).strip().upper()
    if data.get(CONF_AVOID):
        data[CONF_AVOID] = str(data[CONF_AVOID]).strip().upper()

    try:
        # my_api = NationalRailClient(
        #     data[CONF_TOKEN],
        #     data[CONF_STATION],
        #     data[CONF_DESTINATIONS].split(","),
        #     apiTest=False,
        # )
        res = await my_api.async_get_data(
            data[CONF_STATION], data[CONF_DESTINATIONS], apitest=False
        )
        # print(res)
    except NationalRailClientInvalidInput as err:
        _LOGGER.exception(err)
        raise InvalidInput() from err

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    via_suffix = f" via {data[CONF_VIA]}" if data.get(CONF_VIA) else ""
    dest_str = ",".join(data.get(CONF_DESTINATIONS, [])) or "(any)"
    return {"title": f"Train Schedule {data[CONF_STATION]} -> {dest_str}{via_suffix}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for National Rail UK."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        if user_input.get(CONF_STATION):
            user_input[CONF_STATION] = str(user_input[CONF_STATION]).strip().upper()
        if user_input.get(CONF_DESTINATIONS):
            user_input[CONF_DESTINATIONS] = [
                str(d).strip().upper() for d in user_input[CONF_DESTINATIONS]
            ]
        if user_input.get(CONF_VIA):
            user_input[CONF_VIA] = str(user_input[CONF_VIA]).strip().upper()
        if user_input.get(CONF_AVOID):
            user_input[CONF_AVOID] = str(user_input[CONF_AVOID]).strip().upper()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except InvalidToken:
            errors["base"] = "invalid_token"
        except InvalidInput:
            errors["base"] = "invalid_station_input"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class InvalidToken(HomeAssistantError):
    """Error to indicate the Token is invalid."""

    # print("Invalid token called")


class InvalidInput(HomeAssistantError):
    """Error to indicate there is invalid user input."""
