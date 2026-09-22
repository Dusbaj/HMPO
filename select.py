"""Výběry Hyundai HPMO (režim, tichá úroveň, křivka, vynucené dohřevy)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const as C
from .coordinator import HyundaiModbusCoordinator

# (key, adresa, druh, advanced)
# Druhy: mode / silent / curve / forced.
SELECT_DEFS: tuple = (
    ("op_mode_set", C.REG_MODE, "mode", False),
    ("silent_level", C.REG_SILENT_LEVEL, "silent", False),
    ("curve_z1", C.REG_CURVE_Z1, "curve", True),
    ("forced_dhw", C.REG_FORCED_DHW, "forced", True),
    ("forced_tbh", C.REG_FORCED_TBH, "forced", True),
    ("forced_ibh", C.REG_FORCED_IBH, "forced", True),
)


class HyundaiHPSelect(CoordinatorEntity[HyundaiModbusCoordinator], SelectEntity):
    """Výběr nad holding registrem."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HyundaiModbusCoordinator, entry_id: str, definition: tuple) -> None:
        """Inicializace výběru."""
        super().__init__(coordinator)
        key, addr, kind, advanced = definition
        self._key = key
        self._addr = addr
        self._kind = kind
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self.entity_id = f"select.hyundai_hp_{key}"
        if kind == "mode":
            self._attr_options = list(C.SET_MODE_OPTIONS)
        elif kind == "silent":
            self._attr_options = list(C.SILENT_LEVEL_OPTIONS)
        elif kind == "curve":
            self._attr_options = list(C.CURVE_OPTIONS)
        else:
            self._attr_options = list(C.FORCED_OPTIONS)
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

    @property
    def current_option(self) -> str | None:
        """Aktuální volba."""
        raw = self.coordinator.get_reg(self._addr)
        if raw is None:
            return None
        if self._kind == "mode":
            return C.SET_MODE_FROM_REG.get(raw)
        if self._kind == "silent":
            return C.SILENT_LEVEL_FROM_REG.get(raw)
        if self._kind == "curve":
            return str(raw) if 1 <= raw <= 9 else None
        return C.FORCED_FROM_REG.get(raw)

    async def async_select_option(self, option: str) -> None:
        """Zápis volby (06H)."""
        if self._kind == "mode":
            value = C.SET_MODE_TO_REG.get(option)
        elif self._kind == "silent":
            value = C.SILENT_LEVEL_TO_REG.get(option)
        elif self._kind == "curve":
            value = int(option)
        else:
            value = C.FORCED_TO_REG.get(option)
        if value is None:
            return
        await self.coordinator.async_write_register(self._addr, value)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Založení výběrů."""
    coordinator: HyundaiModbusCoordinator = hass.data[C.DOMAIN][entry.entry_id]
    async_add_entities(
        HyundaiHPSelect(coordinator, entry.entry_id, definition)
        for definition in SELECT_DEFS
    )
