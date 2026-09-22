"""Senzory Hyundai HPMO (teploty, tlaky, výkony, energie, chyby)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import const as C
from .coordinator import HyundaiModbusCoordinator

# (key, adresa nebo (hi, lo), druh, jednotka, device_class, state_class,
#  advanced, kategorie, extra)
# Druhy: p1 / p2 / plain = teploty; raw = int; scale = raw*faktor;
# energy32 = kWh z páru (R290 *100); x100 = /100; opmode / hpmode / errtext.
SENSOR_DEFS: tuple = (
    # --- základní (jednoduchý režim) ---
    ("tw_in", C.REG_TW_IN, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("tw_out", C.REG_TW_OUT, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("t1_total", C.REG_T1, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("t5_dhw", C.REG_T5, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("t4_ambient", C.REG_T4, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("ta_room", C.REG_TA, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    ("op_mode", C.REG_OP_MODE, "opmode", None, SensorDeviceClass.ENUM, None, False, None, None),
    ("hp_mode", C.REG_HP_MODE, "hpmode", None, SensorDeviceClass.ENUM, None, False, None, None),
    ("frequency", C.REG_FREQ, "raw", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, False, None, None),
    ("heat_power_rt", C.REG_HEAT_PWR_RT, "x100", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, False, None, None),
    ("heat_cop_rt", C.REG_HEAT_COP_RT, "x100", None, None, SensorStateClass.MEASUREMENT, False, None, None),
    ("heat_energy_total", (C.REG_HEAT_EN_HI, C.REG_HEAT_EN_LO), "energy32", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, False, None, None),
    ("error_code", C.REG_ERROR, "raw", None, None, None, False, None, None),
    ("error_text", C.REG_ERROR, "errtext", None, None, None, False, None, None),
    ("water_flow", C.REG_WATER_FLOW, "x100", UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR, SensorDeviceClass.VOLUME_FLOW, SensorStateClass.MEASUREMENT, False, None, None),
    ("tbt1", C.REG_TBT1, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, False, None, None),
    # --- pokročilé ---
    ("p1", C.REG_P1, "raw", UnitOfPressure.KPA, SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("p2", C.REG_P2, "raw", UnitOfPressure.KPA, SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("tp", C.REG_TP, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("th", C.REG_TH, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("t3", C.REG_T3, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("t2", C.REG_T2, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("t2b", C.REG_T2B, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("fan", C.REG_FAN, "raw", "r/min", None, SensorStateClass.MEASUREMENT, True, None, None),
    ("exv1", C.REG_EXV1, "raw", "P", None, SensorStateClass.MEASUREMENT, True, None, None),
    ("odu_current", C.REG_ODU_CURRENT, "raw", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, True, None, None),
    ("odu_voltage", C.REG_ODU_VOLTAGE, "raw", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, True, None, None),
    ("comp_hours", C.REG_COMP_HOURS, "raw", UnitOfTime.HOURS, SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING, True, None, None),
    ("capacity", C.REG_CAPACITY, "raw", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, None, True, EntityCategory.DIAGNOSTIC, None),
    ("tf", C.REG_TF, "plain", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("t1s_calc", C.REG_T1S_CALC_Z1, "p1", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("tw2", C.REG_TW2, "p2", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, "zone2"),
    ("err_detail", C.REG_ERR_DETAIL, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("dc_current", C.REG_DC_CURRENT, "scale", UnitOfElectricCurrent.AMPERE, SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, True, None, 0.1),
    ("dc_voltage", C.REG_DC_VOLTAGE, "scale", UnitOfElectricPotential.VOLT, SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, True, None, 10.0),
    ("target_freq", C.REG_TARGET_FREQ, "raw", UnitOfFrequency.HERTZ, SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, True, None, None),
    ("idu_sw", C.REG_IDU_SW, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("hmi_sw", C.REG_HMI_SW, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("heat_cons_total", (C.REG_HEAT_CONS_HI, C.REG_HEAT_CONS_LO), "energy32", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, True, None, None),
    ("heat_cop_total", C.REG_HEAT_COP, "x100", None, None, SensorStateClass.MEASUREMENT, True, None, None),
    ("cool_energy_total", (C.REG_COOL_EN_HI, C.REG_COOL_EN_LO), "energy32", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, True, None, None),
    ("cool_eer_total", C.REG_COOL_EER, "x100", None, None, SensorStateClass.MEASUREMENT, True, None, None),
    ("dhw_energy_total", (C.REG_DHW_EN_HI, C.REG_DHW_EN_LO), "energy32", UnitOfEnergy.KILO_WATT_HOUR, SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING, True, None, None),
    ("dhw_cop_total", C.REG_DHW_COP, "x100", None, None, SensorStateClass.MEASUREMENT, True, None, None),
    ("cool_cap_rt", C.REG_COOL_CAP_RT, "x100", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, True, None, None),
    ("dhw_cap_rt", C.REG_DHW_CAP_RT, "x100", UnitOfPower.KILO_WATT, SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, True, None, None),
    ("dhw_cop_rt", C.REG_DHW_COP_RT, "x100", None, None, SensorStateClass.MEASUREMENT, True, None, None),
    ("tl", C.REG_TL, "plain", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT, True, None, None),
    ("pump_pwm", C.REG_PUMP_PWM, "scale", "%", None, SensorStateClass.MEASUREMENT, True, None, 0.1),
    ("status1_raw", C.REG_STATUS1, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("load_raw", C.REG_LOAD, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("status3_raw", C.REG_STATUS3, "raw", None, None, None, True, EntityCategory.DIAGNOSTIC, None),
    ("t5s_setpoint_rb", C.REG_T5S, "plain", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, None, True, EntityCategory.DIAGNOSTIC, None),
    ("t1s_setpoint_rb", C.REG_T1S, "p1", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE, None, True, EntityCategory.DIAGNOSTIC, None),
)


class HyundaiHPSensor(CoordinatorEntity[HyundaiModbusCoordinator], SensorEntity):
    """Jeden registr (nebo pár) jako senzor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HyundaiModbusCoordinator, entry_id: str, definition: tuple) -> None:
        """Inicializace senzoru."""
        super().__init__(coordinator)
        (key, addr, kind, unit, devclass, stateclass, advanced, category, extra) = definition
        self._key = key
        self._addr = addr
        self._kind = kind
        self._extra = extra
        self._advanced = advanced
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self.entity_id = f"sensor.hyundai_hp_{key}"
        if unit is not None:
            self._attr_native_unit_of_measurement = unit
        if devclass is not None:
            self._attr_device_class = devclass
        if stateclass is not None:
            self._attr_state_class = stateclass
        if category is not None:
            self._attr_entity_category = category
        # Zóna 2 je na této jednotce deaktivovaná -> entita vypnutá.
        if extra == "zone2":
            self._attr_entity_registry_enabled_default = False
        elif advanced and coordinator.simple_mode:
            self._attr_entity_registry_enabled_default = False

    @property
    def device_info(self):
        """Zařízení tepelného čerpadla."""
        from homeassistant.helpers.entity import DeviceInfo

        return DeviceInfo(
            identifiers={(C.DOMAIN, f"{self.coordinator.host}:{self.coordinator.slave}")},
            name="Hyundai HPMO-06",
            manufacturer="Hyundai (Klimavex CZ)",
            model="HPMO-06-D2L1H3-A1B",
        )

    def _raw(self, address: int) -> int | None:
        return self.coordinator.get_reg(address)

    @property
    def native_value(self):
        """Aktuální hodnota z cache koordinátoru."""
        tenth = self.coordinator.tenth_degree
        kind = self._kind
        if kind == "energy32":
            hi = self._raw(self._addr[0])
            lo = self._raw(self._addr[1])
            if hi is None or lo is None:
                return None
            return C.energy_kwh(hi, lo)
        raw = self._raw(self._addr)
        if raw is None:
            return None
        if kind == "p1":
            return C.decode_p1(raw, tenth)
        if kind == "p2":
            return C.decode_p2(raw, tenth)
        if kind == "plain":
            return C.decode_plain(raw)
        if kind == "raw":
            return raw
        if kind == "scale":
            return round(raw * float(self._extra), 2)
        if kind == "x100":
            return C.scale_100(raw)
        if kind == "opmode":
            return C.OP_MODE_MAP.get(raw, f"unknown_{raw}")
        if kind == "hpmode":
            return C.HP_MODE_MAP.get(raw, f"unknown_{raw}")
        if kind == "errtext":
            if raw == 0:
                return "OK"
            item = C.ERROR_TABLE.get(raw)
            if item is None:
                return f"unknown_{raw}"
            lang = (self.hass.config.language or "en").lower()
            return f"{item[0]} - {item[2] if lang.startswith('cs') else item[1]}"
        return None

    @property
    def extra_state_attributes(self):
        """U chyb i číselná hodnota a kód."""
        if self._key in ("error_code", "error_text"):
            raw = self._raw(C.REG_ERROR)
            if raw is None:
                return None
            item = C.ERROR_TABLE.get(raw)
            code = item[0] if item else (None if raw == 0 else f"unknown_{raw}")
            return {"error_value": raw, "error_code": code}
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Založení senzorů."""
    coordinator: HyundaiModbusCoordinator = hass.data[C.DOMAIN][entry.entry_id]
    async_add_entities(
        HyundaiHPSensor(coordinator, entry.entry_id, definition)
        for definition in SENSOR_DEFS
    )
