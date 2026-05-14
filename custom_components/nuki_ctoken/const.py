"""Constants for the Nuki ctoken integration."""

DOMAIN = "nuki_ctoken"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_TOKEN = "token"
CONF_NUKI_ID = "nuki_id"
CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_NAME = "device_name"
CONF_SOURCE = "source"
CONF_ENTRY_ID = "entry_id"

DEFAULT_PORT = 8080
REQUEST_TIMEOUT = 10

ACTION_MAP = {
    "unlock": 1,
    "lock": 2,
    "open": 3,
    "lockngo": 4,
    "lockngo_open": 5,
}

SERVICE_NAMES = tuple(ACTION_MAP.keys())
