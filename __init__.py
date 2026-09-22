"""Hyundai Heat Pump (HPMO) — custom integrace přes Modbus TCP."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SIMPLE_MODE,
    CONF_SLAVE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SIMPLE_MODE,
    DEFAULT_SLAVE,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import HyundaiModbusCoordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Integrace se konfiguruje pouze přes UI (config flow)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Založení config entry: koordinátor + platformy."""
    data = {**entry.data, **entry.options}
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, 502)
    slave = data.get(CONF_SLAVE, DEFAULT_SLAVE)
    scan = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    simple = data.get(CONF_SIMPLE_MODE, DEFAULT_SIMPLE_MODE)

    coordinator = HyundaiModbusCoordinator(hass, host, port, slave, scan, simple)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:  # noqa: BLE001 - první spojení nemusí vyjít
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(f"Nelze se připojit na {host}:{port}: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_update_listener(hass: HomeAssistant, updated: ConfigEntry) -> None:
        merged = {**updated.data, **updated.options}
        coordinator.update_options(
            merged[CONF_HOST],
            merged.get(CONF_PORT, 502),
            merged.get(CONF_SLAVE, DEFAULT_SLAVE),
            merged.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            merged.get(CONF_SIMPLE_MODE, DEFAULT_SIMPLE_MODE),
        )
        await coordinator.async_request_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Odebrání entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator: HyundaiModbusCoordinator | None = hass.data.get(DOMAIN, {}).pop(
        entry.entry_id, None
    )
    if coordinator is not None:
        await coordinator.async_shutdown()
    return unload_ok
