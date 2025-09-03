"""Constants for the National Rail UK integration."""

DOMAIN = "nationalrailuk"
DOMAIN_DATA = f"{DOMAIN}_data"
NATIONAL_RAIL_DATA_CLIENT = "data_client"

# Platforms
SENSOR = "sensor"
PLATFORMS = [SENSOR]

WSDL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01"


CONF_TOKEN = "api_token"
CONF_STATION = "station"
CONF_DESTINATIONS = "destinations"

# Journey planner (additional options)
CONF_VIA = "via"
CONF_AVOID = "avoid"
CONF_MAX_CHANGES = "max_changes"
CONF_MIN_INTERCHANGE_MINS = "min_interchange_mins"
CONF_PLANNER_PROVIDER = "planner_provider"
CONF_TRANSPORTAPI_APP_ID = "transportapi_app_id"
CONF_TRANSPORTAPI_APP_KEY = "transportapi_app_key"

# Refresh frequency for the sensor (seconds)
REFRESH = 1

# Polling interval (minutes)
POLLING_INTERVAL = 10
# Backwards-compat alias (old misspelling used in earlier code)
POLLING_INTERVALE = POLLING_INTERVAL

# Increase polling frequency if within X minutes of next departure or if train is late
HIGH_FREQUENCY_REFRESH = 7

# Suggested default update interval for journey planner coordinator (seconds)
DEFAULT_JOURNEY_UPDATE_INTERVAL = 90
