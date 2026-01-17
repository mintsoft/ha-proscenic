"""Support for the Proscenic vacuum cleaner robot."""

import asyncio
import logging
from enum import Enum, IntFlag
from functools import partial
from typing import Dict, Optional, Union

import voluptuous as vol
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.vacuum import (
    ATTR_CLEANED_AREA,
    DOMAIN,
    PLATFORM_SCHEMA,
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from tinytuya import OutletDevice as Device

from .const import (
    ATTR_BRUSH_HEALTH,
    ATTR_CLEANING_TIME,
    ATTR_DEVICE_MODEL,
    ATTR_ERROR,
    ATTR_FILTER_HEALTH,
    ATTR_MOP_EQUIPPED,
    ATTR_RESET_FILTER,
    ATTR_SENSOR_HEALTH,
    ATTR_SIDE_BRUSH_HEALTH,
    ATTR_WATER_SPEED,
    ATTR_WATER_SPEED_LIST,
    CONF_ENABLE_DEBUG,
    CONF_LOCAL_KEY,
    CONF_REMEMBER_FAN_SPEED,
    DATA_KEY,
    DEFAULT_NAME,
    REMEMBER_FAN_SPEED_DELAY,
    SERVICE_SET_WATER_SPEED,
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_LOCAL_KEY): vol.All(str, vol.Length(min=15, max=16)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_REMEMBER_FAN_SPEED, default=False): cv.boolean,
        vol.Optional(CONF_ENABLE_DEBUG, default=False): cv.boolean,
    },
    extra=vol.ALLOW_EXTRA,
)

SUPPORT_PROSCENIC = (
    VacuumEntityFeature.STATE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.CLEAN_SPOT
    | VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
)


class Fault(IntFlag):
    NO_ERROR = 0
    SIDE_BRUSH = 1
    ROLLER_BRUSH = 2
    LEFT_WHEEL = 4
    RIGHT_WHEEL = 8
    DUST_BIN = 16
    OFF_GROUND = 32
    COLLISION_SENSOR = 64
    WATER_TANK = 128
    VIRTUAL_WALL = 256
    TRAPPED = 512
    UNKNOWN = 1024


class CurrentState(Enum):
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: int, ha_state: str):
        self._ha_state_ = ha_state

    @property
    def ha_state(self) -> str:
        """Returns the corresponding state, defined by HA"""
        return self._ha_state_

    STAND_BY = 0, VacuumActivity.IDLE
    CLEAN_SMART = 1, VacuumActivity.CLEANING
    MOPPING = 2, VacuumActivity.CLEANING
    CLEAN_WALL_FOLLOW = 3, VacuumActivity.CLEANING
    GOING_CHARGING = 4, VacuumActivity.RETURNING
    CHARGING = 5, VacuumActivity.DOCKED
    #    ??? = 6, ??? todo find it out
    PAUSE = 7, VacuumActivity.PAUSED
    CLEAN_SINGLE = 8, VacuumActivity.CLEANING


# rw=read/write, ro=read only
class Fields(Enum):
    POWER = 1  # rw
    FAULT = 11  # ro
    CLEANING_MODE = 25  # rw
    DIRECTION_CONTROL = 26  # rw
    FAN_SPEED = 27  # rw
    CURRENT_STATE = 38  # ro
    BATTERY = 39  # ro
    CLEAN_RECORD = 40  # ro
    CLEAN_AREA = 41  # ro
    CLEAN_TIME = 42  # ro
    SENSOR_HEALTH = 44  # ro
    FILTER_HEALTH = 45  # ro
    SIDE_BRUSH_HEALTH = 47  # ro
    BRUSH_HEALTH = 48  # ro
    SWEEP_OR_MOP = 49  # ro
    RESET_FILTER = 52  # ro
    DEVICE_MODEL = 58  # ro
    WATER_SPEED = 60  # rw


class CleaningMode(Enum):
    SMART = "smart"
    WALL_FOLLOW = "wallfollow"
    MOP = "mop"
    CHARGE_GO = "chargego"
    SPRIAL = "sprial"
    #    IDLE="idle" #not settable
    SINGLE = "single"


class DirectionControl(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turnleft"
    TURN_RIGHT = "turnright"
    STOP = "stop"


class FanSpeed(Enum):
    ECO = "ECO"
    NORMAL = "normal"
    STRONG = "strong"


class WaterSpeedMode(Enum):
    LOW = "small"
    MEDIUM = "medium"
    HIGH = "Big"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Proscenic vacuum cleaner robot platform."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config[CONF_HOST]
    device_id = config[CONF_DEVICE_ID]
    local_key = config[CONF_LOCAL_KEY]
    name = config[CONF_NAME]
    remember_fan_speed = config[CONF_REMEMBER_FAN_SPEED]
    enable_debug = config[CONF_ENABLE_DEBUG]

    # Create handler
    _LOGGER.info("Initializing with host %s", host)

    device = Device(device_id, host, local_key)
    device.version = 3.3

    battery = ProscenicVacuumBattery(name)
    robot = ProscenicVacuum(name, device, battery, remember_fan_speed, enable_debug)
    hass.data[DATA_KEY][host] = robot
    hass.data[DATA_KEY][host + "_battery"] = battery

    async_add_entities([robot, battery], update_before_add=True)

    platform = entity_platform.current_platform.get()

    hass.data[DOMAIN].async_register_entity_service(
        SERVICE_SET_WATER_SPEED,
        {vol.Required(ATTR_WATER_SPEED): vol.All(vol.Coerce(str))},
        ProscenicVacuum.async_set_water_speed.__name__,
    )


class ProscenicVacuumBattery(SensorEntity):
    """Battery level for 850T"""

    _attr_native_unit_of_measurement = "%"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name):
        self._battery_level = -1
        self._name = name + " Battery"

    @property
    def name(self):
        return self._name

    @property
    def native_value(self):
        return self._battery_level

    @property
    def icon(self) -> str:
        return "mdi:battery"

    def set_battery(self, new_level):
        self._battery_level = new_level


class ProscenicVacuum(StateVacuumEntity):
    """Representation of a Proscenic Vacuum cleaner robot."""

    def __init__(
        self,
        name: str,
        device: Device,
        battery: ProscenicVacuumBattery,
        remember_fan_speed: bool,
        enable_debug: bool,
    ):
        """Initialize the Proscenic vacuum cleaner robot."""
        self._name = name
        self._device = device
        self._batteryDevice = battery
        self._remember_fan_speed = remember_fan_speed
        self._enable_debug = enable_debug

        self._available = False
        self._current_state: Optional[CurrentState] = None
        self._last_command: Optional[CleaningMode] = None
        self._fault: Fault = Fault.NO_ERROR
        self._fan_speed: FanSpeed = FanSpeed.NORMAL
        self._water_speed: WaterSpeedMode = WaterSpeedMode.MEDIUM
        self._stored_fan_speed: FanSpeed = self._fan_speed
        self._additional_attr: Dict[str, Union[bool, str, int]] = dict()

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the status of the vacuum cleaner."""
        if self._fault != Fault.NO_ERROR:
            if self._enable_debug == True:
                _LOGGER.warning("Fault returned! (%s)", self._fault)
            return VacuumActivity.ERROR

        if self._current_state is None:
            return None
        else:
            return self._current_state.ha_state

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        return self._fan_speed.value

    @property
    def fan_speed_list(self):
        """Get the list of available fan speed steps of the vacuum cleaner."""
        f: FanSpeed
        return [f.value for f in FanSpeed]

    @property
    def water_speed(self):
        """Return the water speed of the vacuum cleaner."""
        return self._water_speed.value

    @property
    def water_speed_list(self):
        """Get the list of available water speed steps of the vacuum cleaner."""
        w: WaterSpeedMode
        return [w.value for w in WaterSpeedMode]

    @property
    def should_poll(self):
        return True

    @property
    def extra_state_attributes(self):
        """Return the specific state attributes of this vacuum cleaner."""
        return self._additional_attr

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_PROSCENIC

    @property
    def direction_list(self):
        """Get the list of available direction controls of the vacuum cleaner."""
        return [d.value for d in DirectionControl]

    async def async_start(self):
        """Start or resume the cleaning task."""
        if self._last_command is not None and self._current_state == CurrentState.PAUSE:
            await self._execute_command(Fields.CLEANING_MODE, self._last_command)
        else:
            await self._execute_command(Fields.CLEANING_MODE, CleaningMode.SMART)

    async def async_pause(self):
        """Pause the cleaning task."""
        if self._last_command is not None and self._current_state != CurrentState.PAUSE:
            await self._execute_command(Fields.CLEANING_MODE, self._last_command)

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        await self._execute_command(Fields.DIRECTION_CONTROL, DirectionControl.STOP)

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        await self._execute_command(Fields.CLEANING_MODE, CleaningMode.CHARGE_GO)

    async def async_clean_spot(self, **kwargs):
        """Perform a spot clean-up."""
        await self._execute_command(Fields.CLEANING_MODE, CleaningMode.SPRIAL)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs):
        """Set fan speed."""
        try:
            value = FanSpeed(fan_speed)
            await self._execute_command(Fields.FAN_SPEED, value)
            self._stored_fan_speed = value
        except Exception:
            _LOGGER.error(
                "Fan speed not recognized (%s). Valid speeds are: %s",
                fan_speed,
                self.fan_speed_list,
            )

    async def async_set_water_speed(self, water_speed: str, **kwargs):
        """Set mop water speed."""
        try:
            value = WaterSpeedMode(water_speed)
            await self._execute_command(Fields.WATER_SPEED, value)
        except Exception:
            _LOGGER.error(
                "Water speed not recognized (%s). Valid speeds are: %s",
                water_speed,
                self.water_speed_list,
            )

    def update(self):
        """Fetch state from the device."""
        try:
            if self._enable_debug == True:
                _LOGGER.warning("About to check the status")
            status = self._device.status()
            if self._enable_debug == True:
                _LOGGER.warning("Status returned control back")
            if "dps" in status:
                self._parse_status_fields(status["dps"])
                self._available = True
            else:
                if self._enable_debug == True:
                    _LOGGER.warning(
                        "'dps' was not included in the status, doing nothing"
                    )
        except Exception as exc:
            _LOGGER.error(
                "Got exception while fetching the state: %s",
                exc,
                exc_info=True,
            )
            self._available = False

    async def async_remote_control(self, direction: str):
        """Move vacuum with remote control mode."""
        try:
            await self._execute_command(
                Fields.DIRECTION_CONTROL, DirectionControl[direction.upper()]
            )
        except KeyError:
            _LOGGER.error(
                "Direction not recognized (%s). Valid directions are: %s",
                direction,
                self.direction_list,
            )

    async def _execute_command(self, field: Fields, value: Enum):
        """Send command to vacuum robot by setting the correct field"""
        try:
            if field == Fields.CLEANING_MODE:
                self._last_command = value
            elif field == Fields.DIRECTION_CONTROL:
                self._last_command = None

            await self.hass.async_add_executor_job(
                partial(self._device.set_value, field.value, value.value)
            )

            if self._remember_fan_speed and field == Fields.CLEANING_MODE:
                await self._wait_and_set_stored_fan_speed()
        except Exception:
            _LOGGER.error("Could not execute command &s with value %s", field, value)

    def _parse_status_fields(self, state: Dict[str, Union[str, int, float, bool]]):
        """Tries to parse the state into the corresponding fields"""
        if self._enable_debug == True:
            _LOGGER.warning("Parsing status fields: %s", list(state.keys()))
        for k, v in state.items():
            try:
                field = Fields(int(k))
                if field in (
                    Fields.POWER,
                    Fields.CLEANING_MODE,
                    Fields.DIRECTION_CONTROL,
                ):
                    continue

                elif field == Fields.FAULT:
                    self._fault = Fault(int(v))
                    # TODO add nice error text
                    if self._fault == Fault.NO_ERROR:
                        # second value (default value) of pop is required, otherwise it will throw an KeyError,
                        # if the key doesn't exists
                        self._additional_attr.pop(ATTR_ERROR, None)
                    else:
                        self._additional_attr[ATTR_ERROR] = self._fault.name

                elif field == Fields.FAN_SPEED:
                    self._fan_speed = FanSpeed(v)

                elif field == Fields.CURRENT_STATE:
                    self._current_state = CurrentState(int(v))

                elif field == Fields.BATTERY:
                    self._batteryDevice.set_battery(int(v))

                elif field == Fields.CLEAN_RECORD:
                    # TODO parsing
                    continue

                elif field == Fields.CLEAN_AREA:
                    self._additional_attr[ATTR_CLEANED_AREA] = v

                elif field == Fields.CLEAN_TIME:
                    self._additional_attr[ATTR_CLEANING_TIME] = int(v)

                elif field == Fields.SWEEP_OR_MOP:
                    self._additional_attr[ATTR_MOP_EQUIPPED] = (
                        False if v == "sweep" else True
                    )

                elif field == Fields.SENSOR_HEALTH:
                    self._additional_attr[ATTR_SENSOR_HEALTH] = int(v)

                elif field == Fields.FILTER_HEALTH:
                    self._additional_attr[ATTR_FILTER_HEALTH] = int(v)

                elif field == Fields.SIDE_BRUSH_HEALTH:
                    self._additional_attr[ATTR_SIDE_BRUSH_HEALTH] = int(v)

                elif field == Fields.BRUSH_HEALTH:
                    self._additional_attr[ATTR_BRUSH_HEALTH] = int(v)

                elif field == Fields.RESET_FILTER:
                    self._additional_attr[ATTR_RESET_FILTER] = v

                elif field == Fields.DEVICE_MODEL:
                    self._additional_attr[ATTR_DEVICE_MODEL] = v

                elif field == Fields.WATER_SPEED:
                    self._water_speed = WaterSpeedMode(v)
                    self._additional_attr[ATTR_WATER_SPEED] = self._water_speed.value
                    self._additional_attr[ATTR_WATER_SPEED_LIST] = self.water_speed_list

            except (KeyError, ValueError):
                if self._enable_debug == True:
                    _LOGGER.warning(
                        "An error occurred during the processing of the following item (%s:%s)",
                        k,
                        v,
                    )

                continue

    async def _wait_and_set_stored_fan_speed(self):
        _LOGGER.debug("Wainting %d seconds before setting the fan speed")
        await asyncio.sleep(REMEMBER_FAN_SPEED_DELAY)

        await self._execute_command(Fields.FAN_SPEED, self._stored_fan_speed)
