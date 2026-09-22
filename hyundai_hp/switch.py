"""Spínače Hyundai HPMO (napájení, ECO, tichý režim, dezinfekce, reset)."""
from __future__ import annotations

import asyncio

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const as C
from .coordinator import HyundaiModbusCoordinator

# (key, device_class, advanced, zdroj)
# Zdroj: ("reg", adresa) = celý registr 0/1 / ("bit", adresa, bit).
SWITCH_DEFS: tuple = (
    ("power_z1", SwitchDeviceClass.SWITCH, False, ("reg", C.REG_PWR_Z1)),
    ("power_dhw", SwitchDeviceClass.SWITCH, False, ("reg", C.REG_PWR_DHW)),
    ("power_room", SwitchDeviceClass.SWITCH, True, ("reg", C.REG_PWR_ROOM)),
    ("eco", SwitchDeviceClass.SWITCH, False, ("bit", C.REG_POWER, C.BIT_POWER_ECO)),
    ("silent", SwitchDeviceClass.SWITCH, False, ("bit", C.REG_POWER, C.BIT_POWER_SILENT)),
    ("disinfection", SwitchDeviceClass.SWITCH, False, ("bit", C.REG_POWER, C.BIT_POWER_DISINFECTION)),
    ("pump_d_circ", SwitchDeviceClass.SWITCH, False, ("bit", C.REG_POWER, C.BIT_POWER_PUMP_D)),
    ("c2_reset", SwitchDeviceClass.SWITCH, True, ("bit", C.REG_POWER, C.BIT_POWER_C2_RESET)),
)


class HyundaiHPSwitch(CoordinatorEntity[HyundaiModbusCoordinator], SwitchEntity):
    """Spínač nad registrem / bitem (read-modify-write)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HyundaiModbusCoordinator, entry_id: str, definition: tuple) -> None:
        """Inicializace spínače."""
        super().__init__(coordinator)
        key, devclass, advanced, source = definition
        self._key = key
        self._source = source
        self._momentary_off_at: float | None = None
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self.entity_id = f"switch.hyundai_hp_{key}"
        if devclass is not None:
            self._attr_device_class = devclass
        if advanced and coordinator.simple_mode:
            self._attr_entity_registry_enabled_default = False

    @property
    def device_info(self) -> DeviceInfo:
        """Zařízení tepelného čerpadla."""
        return DeviceInfo(
            identifiers={(C.DOMAIN, f"{self.coordinator.host}:{self.coordinator.slave}")},
            name="Hyundai HPMO-06",
            manufacturer="Hyundai (Klimavex CZ)",
            model="HPMO-06-D2L1H3-A1B",
        )

    def _current_raw(self) -> int | None:
        return self.coordinator.get_reg(self._source[1])

    @property
    def is_on(self) -> bool | None:
        """Aktuální stav."""
        raw = self._current_raw()
        if raw is None:
            return None
        if self._source[0] == "reg":
            return raw != 0
        return bool(raw & (1 << self._source[2]))

    async def async_turn_on(self, **kwargs) -> None:
        """Zapnutí."""
        if self._key == "c2_reset":
            await self.coordinator.async_write_bit(
                self._source[1], self._source[2], True
            )
            # Momentový reset: po 5 s bit zase shodíme.
            loop = asyncio.get_running_loop()
            self._momentary_off_at = loop.time() + 5
            await asyncio.sleep(5)
            await self.coordinator.async_write_bit(
                self._source[1], self._source[2], False
            )
            return
        if self._source[0] == "reg":
            await self.coordinator.async_write_register(self._source[1], 1)
        else:
            await self.coordinator.async_write_bit(
                self._source[1], self._source[2], True
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Vypnutí."""
        if self._key == "c2_reset":
            await self.coordinator.async_write_bit(
                self._source[1], self._source[2], False
            )
            return
        if self._source[0] == "reg":
            await self.coordinator.async_write_register(self._source[1], 0)
        else:
            await self.coordinator.async_write_bit(
                self._source[1], self._source[2], False
            )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Založení spínačů."""
    coordinator: HyundaiModbusCoordinator = hass.data[C.DOMAIN][entry.entry_id]
    async_add_entities(
        HyundaiHPSwitch(coordinator, entry.entry_id, definition)
        for definition in SWITCH_DEFS
    )
