import asyncio
import logging
from math import ceil

from xcomfort.devices import Light

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, VERBOSE
from .hub import XComfortHub

_LOGGER = logging.getLogger(__name__)


def log(msg: str):
    if VERBOSE:
        _LOGGER.info(msg)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub = XComfortHub.get_hub(hass, entry)

    devices = hub.devices

    _LOGGER.info(f"Found {len(devices)} xcomfort devices")

    lights = list()
    for device in devices:
        if isinstance(device, Light):
            _LOGGER.info(f"Adding {device}")
            light = HASSXComfortLight(hass, hub, device)
            lights.append(light)

    _LOGGER.info(f"Added {len(lights)} lights")
    async_add_entities(lights)


class HASSXComfortLight(LightEntity):
    def __init__(self, hass: HomeAssistant, hub: XComfortHub, device: Light):
        self.hass = hass
        self.hub = hub

        self._device = device
        self._name = device.name
        self._state = None
        self.device_id = device.device_id

        self._unique_id = f"light_{DOMAIN}_{hub.identifier}-{device.device_id}"

    async def async_added_to_hass(self):
        log(f"Added to hass {self._name} ")
        if self._device.state is None:
            log(f"State is null for {self._name}")
        else:
            self._device.state.subscribe(lambda state: self._state_change(state))

    def _state_change(self, state):
        self._state = state

        should_update = self._state is not None

        log(f"State changed {self._name} : {state}")

        if should_update:
            self.schedule_update_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": "Eaton",
            "model": "XXX",
            "sw_version": "Unknown",
            "via_device": self.hub.hub_id,
        }

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def brightness(self):
        """Return the brightness of the light."""
        if self._state and self._state.dimmvalue is not None:
            return int(255.0 * self._state.dimmvalue / 99.0)
        return None

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state.switch if self._state else False

    @property
    def supported_color_modes(self):
        """Return supported color modes."""
        return {ColorMode.BRIGHTNESS} if self._device.dimmable else {ColorMode.ONOFF}

    @property
    def color_mode(self):
        """Return the color mode."""
        return ColorMode.BRIGHTNESS if self._device.dimmable else ColorMode.ONOFF

    async def async_turn_on(self, **kwargs):
        log(f"async_turn_on {self._name} : {kwargs}")
        if ATTR_BRIGHTNESS in kwargs and self._device.dimmable:
            br = ceil(kwargs[ATTR_BRIGHTNESS] * 99 / 255.0)
            log(f"async_turn_on br {self._name} : {br}")
            await self._device.dimm(br)
            self._state.dimmvalue = br
            self.schedule_update_ha_state()
            return

        switch_task = self._device.switch(True)
        await switch_task

        self._state.switch = True
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        log(f"async_turn_off {self._name} : {kwargs}")
        switch_task = self._device.switch(False)
        await switch_task

        self._state.switch = False
        self.schedule_update_ha_state()

    def update(self):
        pass
