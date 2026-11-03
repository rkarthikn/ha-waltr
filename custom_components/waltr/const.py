"""Constants for the Waltr integration."""

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "waltr"
MANUFACTURER = "Waltr"

API_BASE = "https://api.waltr.in/v0"

# Waltr reports every timestamp and daily bucket in IST.
WALTR_TZ = ZoneInfo("Asia/Kolkata")

SCAN_INTERVAL = timedelta(seconds=60)
DAILY_INTERVAL = timedelta(minutes=15)
# The API allows 5 requests per second; stay under it.
MIN_REQUEST_GAP = 0.25

KIND_TANK = "tank"
KIND_MOTOR = "motor"
KIND_BOREWELL = "borewell"
KIND_VALVE = "valve"
KINDS = (KIND_TANK, KIND_MOTOR, KIND_BOREWELL, KIND_VALVE)

MODELS = {
    "waltr_A": "Waltr A tank sensor",
    "waltr_B": "Waltr B borewell controller",
    "waltr_C": "Waltr C motor controller",
    "waltr_V": "Waltr V valve controller",
}

# Motor and borewell status codes.
PUMP_STATUS = {0: "off", 1: "on", 2: "offline", 3: "malfunction"}
# Valve status codes.
VALVE_STATUS = {0: "closed", 1: "open", 2: "offline", 3: "malfunction"}

STATUS_OFFLINE = 2
STATUS_MALFUNCTION = 3

# A TDS reading of 99 means the sensor is unavailable.
TDS_UNAVAILABLE = 99

DEFAULT_RUN_MINUTES = 30
