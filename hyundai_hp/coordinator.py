"""Modbus koordinátor pro Hyundai HPMO (čtení + bezpečný zápis)."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BIT_TEMP_PRECISION,
    CONF_SCAN_INTERVAL,
    CONF_SIMPLE_MODE,
    CONF_SLAVE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REG_TEMP_FORMAT,
)

_LOGGER = logging.getLogger(__name__)

# Čtecí rozsahy: (start, počet). Vždy čteme řízení 0-20 a provoz 100-199.
# V pokročilém režimu navíc limity 200-209 a nastavení 210-289.
READ_RANGES_SIMPLE = [(0, 21), (100, 100)]
READ_RANGES_ADVANCED = [(0, 21), (100, 100), (200, 10), (210, 80)]

# Čtení dělíme na bloky, aby most Waveshare/čerpadlo nebyl přetížen.
MAX_READ_CHUNK = 64
MAX_CONSECUTIVE_FAILURES = 3


class HyundaiModbusCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Periodické čtení registrů + read-modify-write zápis."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        slave: int,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        simple_mode: bool = True,
    ) -> None:
        """Inicializace koordinátoru."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self.slave = slave
        self.simple_mode = simple_mode
        self._client = None
        self._lock = asyncio.Lock()
        self._failures = 0

    # -- připojení ---------------------------------------------------
    def _get_client(self):
        from pymodbus.client import AsyncModbusTcpClient

        if self._client is None:
            self._client = AsyncModbusTcpClient(
                host=self.host, port=self.port, timeout=5, retries=0
            )
        return self._client

    async def async_shutdown(self) -> None:
        """Uzavření TCP spojení."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001 - uklizení nesmí padnout
                pass
            self._client = None

    async def _ensure_connected(self) -> bool:
        client = self._get_client()
        try:
            connected = client.connected
        except Exception:  # noqa: BLE001
            connected = False
        if connected:
            return True
        try:
            return bool(await asyncio.wait_for(client.connect(), timeout=10))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Modbus connect %s:%s selhal: %s", self.host, self.port, err)
            return False

    # -- čtení -------------------------------------------------------
    def _ranges(self) -> list[tuple[int, int]]:
        ranges = READ_RANGES_SIMPLE if self.simple_mode else READ_RANGES_ADVANCED
        chunked: list[tuple[int, int]] = []
        for start, count in ranges:
            rest = count
            addr = start
            while rest > 0:
                take = min(rest, MAX_READ_CHUNK)
                chunked.append((addr, take))
                addr += take
                rest -= take
        return chunked

    async def _read_range(self, address: int, count: int) -> list[int] | None:
        client = self._get_client()
        try:
            resp = await asyncio.wait_for(
                client.read_holding_registers(
                    address=address, count=count, slave=self.slave
                ),
                timeout=10,
            )
        except TypeError:
            # Starší pymodbus používá `unit` místo `slave`.
            resp = await asyncio.wait_for(
                client.read_holding_registers(
                    address=address, count=count, unit=self.slave
                ),
                timeout=10,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Čtení %s+%s selhalo: %s", address, count, err)
            return None
        try:
            if resp is None or resp.isError():
                _LOGGER.debug("Čtení %s+%s vrátilo chybu: %s", address, count, resp)
                return None
        except Exception:  # noqa: BLE001
            return None
        return list(resp.registers)

    async def _async_update_data(self) -> dict[int, int]:
        """Hlavní polling. Vrací slovník adresa->hodnota."""
        async with self._lock:
            if not await self._ensure_connected():
                return self._handle_failure("nelze se připojit")
            merged: dict[int, int] = dict(self.data or {})
            ok = False
            for address, count in self._ranges():
                regs = await self._read_range(address, count)
                if regs is None:
                    continue
                ok = True
                for offset, value in enumerate(regs):
                    merged[address + offset] = value
            if not ok:
                return self._handle_failure("všechna čtení selhala")
            self._failures = 0
            return merged

    def _handle_failure(self, reason: str) -> dict[int, int]:
        self._failures += 1
        _LOGGER.warning(
            "Modbus %s:%s: %s (%s. selhání)", self.host, self.port, reason, self._failures
        )
        if self._failures >= MAX_CONSECUTIVE_FAILURES:
            raise UpdateFailed(f"Modbus {self.host}:{self.port}: {reason}")
        return dict(self.data or {})

    # -- zápis -------------------------------------------------------
    async def async_write_register(self, address: int, value: int) -> bool:
        """Zápis jednoho registru (06H). Vrací True při úspěchu."""
        async with self._lock:
            if not await self._ensure_connected():
                return False
            client = self._get_client()
            try:
                try:
                    resp = await asyncio.wait_for(
                        client.write_register(
                            address=address, value=value, slave=self.slave
                        ),
                        timeout=10,
                    )
                except TypeError:
                    resp = await asyncio.wait_for(
                        client.write_register(
                            address=address, value=value, unit=self.slave
                        ),
                        timeout=10,
                    )
                if resp is None or resp.isError():
                    _LOGGER.warning("Zápis %s=%s selhal: %s", address, value, resp)
                    return False
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Zápis %s=%s selhal: %s", address, value, err)
                return False
            data = dict(self.data or {})
            data[address] = value
            self.async_set_updated_data(data)
            return True

    async def async_write_bit(self, address: int, bit: int, on: bool) -> bool:
        """Read-modify-write jednoho bitu (ostatní bity zachovány)."""
        async with self._lock:
            current = (self.data or {}).get(address)
            if current is None:
                regs = await self._read_range(address, 1)
                if not regs:
                    return False
                current = regs[0]
            new_value = (current | (1 << bit)) if on else (current & ~(1 << bit))
            if new_value == current:
                return True
            if not await self._ensure_connected():
                return False
            client = self._get_client()
            try:
                try:
                    resp = await asyncio.wait_for(
                        client.write_register(
                            address=address, value=new_value, slave=self.slave
                        ),
                        timeout=10,
                    )
                except TypeError:
                    resp = await asyncio.wait_for(
                        client.write_register(
                            address=address, value=new_value, unit=self.slave
                        ),
                        timeout=10,
                    )
                if resp is None or resp.isError():
                    _LOGGER.warning(
                        "Zápis bitu %s:%s selhal: %s", address, bit, resp
                    )
                    return False
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Zápis bitu %s:%s selhal: %s", address, bit, err)
                return False
            data = dict(self.data or {})
            data[address] = new_value
            self.async_set_updated_data(data)
            return True

    # -- pomocné čtení z cache ---------------------------------------
    def get_reg(self, address: int) -> int | None:
        """Hodnota registru z poslední aktualizace (None = neznámá)."""
        return (self.data or {}).get(address)

    @property
    def tenth_degree(self) -> bool:
        """Formát teplot 0,1 °C? (bit8 registru 189)."""
        raw = self.get_reg(REG_TEMP_FORMAT)
        if raw is None:
            return False
        return bool(raw & (1 << BIT_TEMP_PRECISION))

    def update_options(
        self, host: str, port: int, slave: int, scan_interval: int, simple_mode: bool
    ) -> None:
        """Aplikace změn z OptionsFlow (nové spojení + interval)."""
        changed_conn = (host, port, slave) != (self.host, self.port, self.slave)
        self.host = host
        self.port = port
        self.slave = slave
        self.simple_mode = simple_mode
        self.update_interval = timedelta(seconds=scan_interval)
        if changed_conn:
            self._client = None
        self._failures = 0
