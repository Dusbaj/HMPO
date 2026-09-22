"""Config flow: hostitel (Waveshare), port, slave ID, interval, režim."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SIMPLE_MODE,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SIMPLE_MODE,
    DEFAULT_SLAVE,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


def _base_schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
            vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
            vol.Optional(CONF_SLAVE, default=defaults.get(CONF_SLAVE, DEFAULT_SLAVE)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=247)
            ),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(
                vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
            ),
            vol.Optional(
                CONF_SIMPLE_MODE,
                default=defaults.get(CONF_SIMPLE_MODE, DEFAULT_SIMPLE_MODE),
            ): bool,
        }
    )


class HyundaiHPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Průvodce přidáním tepelného čerpadla."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """První (a jediný) krok: připojení."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = (user_input.get(CONF_HOST) or "").strip()
            if not host:
                errors[CONF_HOST] = "required"
            else:
                unique = f"{host}:{user_input.get(CONF_PORT, DEFAULT_PORT)}:{user_input.get(CONF_SLAVE, DEFAULT_SLAVE)}"
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                # Rychlý test spojení (nepovinný — chyba neblokuje, jen varuje)
                ok = await self._test_connection(
                    host,
                    user_input.get(CONF_PORT, DEFAULT_PORT),
                    user_input.get(CONF_SLAVE, DEFAULT_SLAVE),
                )
                if not ok:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title=f"Hyundai HP ({host})", data=user_input
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=_base_schema(user_input or {}),
            errors=errors,
        )

    async def _test_connection(self, host: str, port: int, slave: int) -> bool:
        """Krátký pokus o přečtení registru 101 (režim)."""
        try:
            from pymodbus.client import AsyncModbusTcpClient

            client = AsyncModbusTcpClient(host=host, port=port, timeout=5, retries=0)
            connected = await client.connect()
            if not connected:
                return False
            try:
                try:
                    resp = await client.read_holding_registers(
                        address=101, count=1, slave=slave
                    )
                except TypeError:
                    resp = await client.read_holding_registers(
                        address=101, count=1, unit=slave
                    )
                return resp is not None and not resp.isError()
            finally:
                client.close()
        except Exception:  # noqa: BLE001 - test nesmí shodit flow
            return False

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Options flow pro změnu IP/portu bez mazání integrace."""
        return HyundaiHPOptionsFlow()


class HyundaiHPOptionsFlow(config_entries.OptionsFlow):
    """Změna připojení a režimu po instalaci."""

    async def async_step_init(self, user_input: dict | None = None):
        """Formulář voleb."""
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=_base_schema(current),
        )
