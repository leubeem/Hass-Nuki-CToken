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

PLATFORMS = ["lock", "sensor", "binary_sensor"]

# Device types
DEVICE_TYPE_SMART_LOCK = 0
DEVICE_TYPE_OPENER = 2
DEVICE_TYPE_SMART_DOOR = 3
DEVICE_TYPE_SMART_LOCK_PRO = 4

# Smart Lock state codes
SL_STATE_LOCKED = 1
SL_STATE_UNLOCKING = 2
SL_STATE_UNLATCHED = 3
SL_STATE_LOCKING = 4
SL_STATE_UNLATCHING = 6
SL_STATE_MOTOR_BLOCKED = 254

# Opener state codes
OP_STATE_ONLINE = 1       # not active → treated as "locked"
OP_STATE_RTO_ACTIVE = 3   # ring to open active → treated as "unlocked"
OP_STATE_OPEN = 5         # open → treated as "unlocked"
OP_STATE_OPENING = 7      # opening → treated as "unlocking"

# Door sensor state codes
DOOR_STATE_CLOSED = 2
DOOR_STATE_OPEN = 3

ACTION_MAP = {
    "unlock": 1,
    "lock": 2,
    "open": 3,
    "lockngo": 4,
    "lockngo_open": 5,
}

SERVICE_NAMES = tuple(ACTION_MAP.keys())

LOG_ACTION_NAMES: dict[int, str] = {
    1: "unlock",
    2: "lock",
    3: "unlatch",
    4: "lock'n'go",
    5: "lock'n'go + unlatch",
    208: "door opened",
    209: "door closed",
    210: "door sensor jammed",
}

LOG_TRIGGER_NAMES: dict[int, str] = {
    0: "system",
    1: "manual",
    2: "button",
    3: "auto-lock",
    4: "app",
    6: "automatic",
    255: "unknown",
}

MODEL_NAMES: dict[int, str] = {
    DEVICE_TYPE_SMART_LOCK: "Smart Lock",
    DEVICE_TYPE_OPENER: "Opener",
    DEVICE_TYPE_SMART_DOOR: "Smart Door",
    DEVICE_TYPE_SMART_LOCK_PRO: "Smart Lock Pro",
}
