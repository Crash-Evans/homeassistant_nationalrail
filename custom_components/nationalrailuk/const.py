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

# Refresh frequency for the sensor
REFRESH = 1

# Polling interval (in minutes)
POLLING_INTERVALE = 10

# Increase polling frequency if withing X minutes of next departure or if train is late
HIGH_FREQUENCY_REFRESH = 7
