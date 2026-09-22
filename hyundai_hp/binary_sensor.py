"""Binární senzory Hyundai HPMO (provozní stavy, čerpadla, dohřevy, chyba)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const as C
from .coordinator import HyundaiModbusCoordinator

# (key, device_class, advanced, zdroj)
# Zdroj: ("bit", adresa, bit) / ("hp_eq", hodnota) / ("err", None) /
#        ("load_comb", bity) - IBH = IBH1 nebo IBH2.
BINARY_DEFS: tuple = (
    ("error_active", BinarySensorDeviceClass.PROBLEM, False, ("err", None)),
    ("heating_active", BinarySensorDeviceClass.RUNNING, False, ("hp_eq", 3)),
    ("cooling_active", BinarySensorDeviceClass.RUNNING, False, ("hp_eq", 2)),
    ("dhw_active", BinarySensorDeviceClass.RUNNING, False, ("hp_eq", 5)),
    ("defrost", BinarySensorDeviceClass.RUNNING, False, ("bit", C.REG_STATUS1, C.BIT_ST1_DEFROST)),
    ("antifreeze", BinarySensorDeviceClass.RUNNING, False, ("bit", C.REG_STATUS1, C.BIT_ST1_ANTIFREEZE)),
    ("pump_i", BinarySensorDeviceClass.RUNNING, False, ("bit", C.REG_LOAD, C.BIT_LOAD_PUMP_I)),
    ("pump_d", BinarySensorDeviceClass.RUNNING, False, ("bit", C.REG_LOAD, C.BIT_LOAD_PUMP_D)),
    ("tbh_on", BinarySensorDeviceClass.HEAT, False, ("bit", C.REG_LOAD, C.BIT_LOAD_TBH)),
    ("ibh_on", BinarySensorDeviceClass.HEAT, False, ("load_comb", (C.BIT_LOAD_IBH1, C.BIT_LOAD_IBH2))),
    ("alarm", BinarySensorDeviceClass.PROBLEM, True, ("bit", C.REG_STATUS1, C.BIT_ST1_ALARM)),
    ("oil_return", BinarySensorDeviceClass.RUNNING, True, ("bit", C.REG_STATUS1, C.BIT_ST1_OIL)),
    ("pump_o", BinarySensorDeviceClass.RUNNING, True, ("bit", C.REG_LOAD, C.BIT_LOAD_PUMP_O)),
)


class HyundaiHPBinarySensor(CoordinatorEntity[HyundaiModbusCoordinator], BinarySensorEntity):
    """Stavový bit / odvozený stav jako binární senzor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HyundaiModbusCoordinator, entry_id: str, definition: tuple) -> None:
        """Inicializace binárního senzoru."""
        super().__init__(coordinator)
        key, devclass, advanced, source = definition
        self._key = key
        self._source = source
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self.entity_id = f"binary_sensor.hyundai_hp_{key}"
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

    @property
    def is_on(self) -> bool | None:
        """Aktuální stav."""
        kind, arg = self._source[0], self._source[1]
        if kind == "err":
            raw = self.coordinator.get_reg(C.REG_ERROR)
            return None if raw is None else raw != 0
        if kind == "hp_eq":
            raw = self.coordinator.get_reg(C.REG_HP_MODE)
            return None if raw is None else raw == arg
        if kind == "bit":
            raw = self.coordinator.get_reg(arg)
            bit = self._source[2]
            return None if raw is None else bool(raw & (1 << bit))
        if kind == "load_comb":
            raw = self.coordinator.get_reg(C.REG_LOAD)
            if raw is None:
                return None
            return any(bool(raw & (1 << b)) for b in arg)
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Založení binárních senzorů."""
    coordinator: HyundaiModbusCoordinator = hass.data[C.DOMAIN][entry.entry_id]
    async_add_entities(
        HyundaiHPBinarySensor(coordinator, entry.entry_id, definition)
        for definition in BINARY_DEFS
    )
