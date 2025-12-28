"""Constants for the proscenic integration."""

from homeassistant.components.vacuum import DOMAIN as VACUUM_DOMAIN

DOMAIN = "proscenic-850t-localtuya"
DEFAULT_NAME = "Proscenic 850T Vacuum"
DATA_KEY = f"{VACUUM_DOMAIN}.{DOMAIN}"

CONF_LOCAL_KEY = "local_key"
CONF_REMEMBER_FAN_SPEED = "remember_fan_speed"
CONF_ENABLE_DEBUG = "enable_debug"

SERVICE_SET_WATER_SPEED = "set_water_speed"

ATTR_MOP_EQUIPPED = "mop_equipped"
ATTR_CLEANING_TIME = "cleaning_time"
ATTR_ERROR = "error"
ATTR_DEVICE_MODEL = "device_model"
ATTR_RESET_FILTER = "reset_filter"
ATTR_FILTER_HEALTH = "filter_health"
ATTR_SIDE_BRUSH_HEALTH = "side_brush_health"
ATTR_BRUSH_HEALTH = "brush_health"
ATTR_SENSOR_HEALTH = "sensor_health"
ATTR_WATER_SPEED = "water_speed"
ATTR_WATER_SPEED_LIST = "water_speed_list"

# in seconds
REMEMBER_FAN_SPEED_DELAY = 6
