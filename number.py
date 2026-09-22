"""Číselné vstupy Hyundai HPMO (žádané teploty, časy)."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const as C
from .coordinator import HyundaiModbusCoordinator

# (key, adresa, druh, jednotka, min_limit_reg, max_limit_reg,
#  fallback_min, fallback_max, krok, advanced, trvale_vypnuto)
# Druhy: p1 / p2 / plain. Limity: protokol = skutečnost*2 (T1s, T5s).
NUMBER_DEFS: tuple = (
    ("t1s", C.REG_T1S, "p1", UnitOfTemperature.CELSIUS,
     C.REG_LIM_T1H_LO, C.REG_LIM_T1H_HI,
     C.FALLBACK_T1S_MIN, C.FALLBACK_T1S_MAX, 0.5, False, False),
    ("t5s", C.REG_T5S, "plain", UnitOfTemperature.CELSIUS,
     C.REG_LIM_T5_LO, C.REG_LIM_T5_HI,
     C.FALLBACK_T5S_MIN, C.FALLBACK_T5S_MAX, 1.0, False, False),
    ("tas", C.REG_TAS, "p2", UnitOfTemperature.CELSIUS,
     C.REG_LIM_TA_LO, C.REG_LIM_TA_HI,
     C.FALLBACK_TAS_MIN, C.FALLBACK_TAS_MAX, 0.5, False, False),
    # Zóna 2 je deaktivovaná -> entita po instalaci vypnutá.
    ("t1s2", C.REG_T1S2, "p1", UnitOfTemperature.CELSIUS,
     C.REG_LIM_T1H_LO, C.REG_LIM_T1H_HI,
     C.FALLBACK_T1S_MIN, C.FALLBACK_T1S_MAX, 0.5, True, True),
    ("sgmax", C.REG_SG_MAX, "plain", UnitOfTime.HOURS,
     None, None, 0.0, 24.0, 1.0, True, False),
    ("pumpd_time", C.REG_PUMP_D_TIME, "plain", UnitOfTime.MINUTES,
     None, None, 5.0, 120.0, 1.0, True, False),
)


class HyundaiHPNumber(CoordinatorEntity[HyundaiModbusCoordinator], NumberEntity):
    """Žádaná hodnota nad holding registrem."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: HyundaiModbusCoordinator, entry_id: str, definition: tuple) -> None:
        """Inicializace číselného vstupu."""
        super().__init__(coordinator)
        (key, addr, kind, unit, lo_reg, hi_reg, fb_min, fb_max, step, advanced, disabled) = definition
        self._key = key
        self._addr = addr
        self._kind = kind
        self._lo_reg = lo_reg
        self._hi_reg = hi_reg
        self._fb_min = fb_min
        self._fb_max = fb_max
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = NumberDeviceClass.TEMPERATURE if unit == UnitOfTemperature.CELSIUS else None
        self._attr_native_step = step
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self.entity_id = f"number.hyundai_hp_{key}"
        if disabled:
            self._attr_entity_registry_enabled_default = False
        elif advanced and coordinator.simple_mode:
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

    def _decode(self, raw: int) -> float | None:
        tenth = self.coordinator.tenth_degree
        if self._kind == "p1":
            return C.decode_p1(raw, tenth)
        if self._kind == "p2":
            return C.decode_p2(raw, tenth)
        return C.decode_plain(raw)

    def _encode(self, value: float) -> int:
        tenth = self.coordinator.tenth_degree
        if self._kind == "p1":
            return C.encode_p1(value, tenth)
        if self._kind == "p2":
            return C.encode_p2(value, tenth)
        return int(round(value))

    @property
    def native_value(self) -> float | None:
        """Aktuální žádaná hodnota."""
        raw = self.coordinator.get_reg(self._addr)
        return None if raw is None else self._decode(raw)

    def _limit(self, reg: int | None, fallback: float) -> float:
        if reg is None:
            return fallback
        raw = self.coordinator.get_reg(reg)
        if raw is None:
            return fallback
        # Limity T1s/T5s: protokol = skutečnost*2 (strana 7 manuálu).
        if self._key in ("t1s", "t1s2", "t5s"):
            return round(raw / 2.0, 1)
        return float(raw)

    @property
    def native_min_value(self) -> float:
        """Dolní mez (z jednotky, jinak záloha)."""
        return self._limit(self._lo_reg, self._fb_min)

    @property
    def native_max_value(self) -> float:
        """Horní mez (z jednotky, jinak záloha)."""
        return self._limit(self._hi_reg, self._fb_max)

    async def async_set_native_value(self, value: float) -> None:
        """Zápis žádané hodnoty (06H)."""
        lo = self.native_min_value
        hi = self.native_max_value
        clamped = max(lo, min(hi, value))
        await self.coordinator.async_write_register(self._addr, self._encode(clamped))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Založení číselných vstupů."""
    coordinator: HyundaiModbusCoordinator = hass.data[C.DOMAIN][entry.entry_id]
    async_add_entities(
        HyundaiHPNumber(coordinator, entry.entry_id, definition)
        for definition in NUMBER_DEFS
    )
