# Hyundai Heat Pump (HPMO) — vlastní integrace pro Home Assistant

Vlastní integrace pro tepelné čerpadlo **Hyundai Monoblok R290
(HPMO-04 až HPMO-16)** přes Modbus. Otestováno na **HPMO-06, 1-fáz,
Zóna 1 + TUV** (Zóna 2 deaktivovaná) s převodníkem
**Waveshare RS485-to-ETH-B**.

Po instalaci se v HA objeví nová dlaždice **Hyundai tepelné čerpadlo
(HPMO)** — senzory, spínače, nastavení teplot, volba režimu.

## 1. Zapojení

1. Na čerpadle najdi svorky Modbusu: **H1 = „−"**, **H2 = „+"**
   (RS-485, manuál strana 1).
2. Připoj je na RS-485 stranu převodníku Waveshare
   (A ↔ H1, B ↔ H2 — při prohození komunikace nepojede, nic se nezničí).
3. Waveshare zapoj do LAN a v jeho webovém rozhraní nastav:
   - režim **Modbus TCP to RTU gateway** (brána),
   - TCP port **502** (nebo vlastní — ten pak zadáš v HA),
   - sériový port **9600, 8 datových bitů, bez parity, 1 stop bit (8N1)**.
4. Převodníku dej **statickou IP** (rezervace v DHCP routeru).
5. Na drátovém ovladači čerpadla v servisním menu (**FOR SERVICEMAN**)
   zkontroluj **HMI Address for BMS** — typicky **1**.
   Tato adresa = slave ID v integraci. Bez kaskády je vždy 1.

## 2. Instalace integrace

### Varianta A — přes HACS (doporučeno)

1. HACS → Integrace → ⋮ → **Vlastní repozitáře** → vlož URL tohoto
   repozitáře, kategorie **Integrace** → Přidat.
2. Vyhledej **Hyundai Heat Pump (HPMO)** → Stáhnout → **Restartuj HA**.
3. Nastavení → Zařízení a služby → **Přidat integraci** →
   **Hyundai tepelné čerpadlo (HPMO)** → vyplň:
   - hostitel = IP převodníku (např. `192.168.1.50`),
   - port = `502`, slave = `1`, interval = `15` s,
   - jednoduchý režim = **zapnuto** (jen základní entity).
4. Hotovo — objeví se zařízení **Hyundai HPMO-06** s entitami.

### Varianta B — ručně

1. Složku `custom_components/hyundai_hp` zkopíruj do
   `/config/custom_components/hyundai_hp` na HA Green
   (přes File editor, Samba nebo SSH).
2. Restartuj Home Assistant.
3. Pokračuj bodem 3 z varianty A.

> IP adresa **není nikde natvrdo** — zadává se v průvodci a kdykoliv
> se dá změnit v **Nastavení → Zařízení a služby → Hyundai HP →
> Konfigurovat** (options flow), bez mazání integrace.

## 3. Jednoduchý vs. pokročilý režim

- **Jednoduchý režim (výchozí):** aktivní jsou jen klíčové entity —
  napájení Zóna 1 + TUV, režim, žádané teploty T1s/T5s/Tas, ECO,
  tichý režim, dezinfekce, cirkulace TUV, hlavní teploty, výkon,
  COP, energie, chyba. Ideální na kartu **Vybrané**.
- **Pokročilý režim:** vypni volbu v Konfigurovat → zpřístupní se
  všechny registry (tlaky, proudy, křivky, časy, kumulované energie
  chlazení/TUV, surová stavová slova). Ideální na kartu **Vše**.

V kartě **Vše** si pak v HA vybereš entity, které si přidáš do karty
**Vybrané** (Upravit dashboard → Přidat kartu → Podle entity).

## 4. Dashboard (2 záložky)

Soubor `dashboard_lovelace.yaml` obsahuje 2 zobrazení:

- **TČ Vybrané** — stav, teploty, výkon/COP, ovládání (režim, teploty,
  spínače), chyba.
- **TČ Vše** — všechny entity včetně diagnostiky.

Import: nový dashboard (Nastavení → Dashboarde → Přidat) → ⋮ →
**Upravit jako YAML** → vlož obsah souboru → entity ID sedí
(`sensor.hyundai_hp_*`, `switch.hyundai_hp_*`, …), nic se nepřepisuje.

## 5. Ověření po instalaci (pošli výsledky)

1. Vývojářské nástroje → **Stavy** → vyhledej `hyundai_hp`:
   - `sensor.hyundai_hp_tw_out` ukazuje reálnou teplotu vody?
   - `sensor.hyundai_hp_t4_ambient` sedí s venkovní teplotou?
   - `sensor.hyundai_hp_error_text` = `OK`?
2. Zkus změnit `number.hyundai_hp_t1s` o 1 °C → projeví se na ovladači?
3. Zkus `switch.hyundai_hp_eco` zapnout/vypnout.
4. Nastavení → Systém → **Protokoly** → vyhledej `hyundai_hp` —
   pošli případné chyby.

Srovnávací hodnoty čti z drátového ovladače čerpadla ve stejnou chvíli.

## 6. Bezpečnost a známá omezení

- Registry **200–208 jsou jen ke čtení** — integrace do nich nezapisuje.
- Zápisy jdou přes **read-modify-write** (bitová pole se nemrví).
- **Nezapisuj** do registrů 210/211 a 250+ bez znalosti významu
  (konfigurace instalatéra) — proto jsou mimo entity.
- Škálování teplot se řídí bitem 8 registru 189
  (1 °C vs. 0,1 °C) — integrace ho čte automaticky.
  Energetické registry R290 se dělí 100 (kWh).
- Stavové bity 128/198 jsou v manuálu popsány nejednoznačně —
  entity `defrost`, `antifreeze` apod. **ověř naživo** proti displeji.
- Interval dotazování pod 10 s zbytečně zatěžuje sběrnici.

## 7. Soubory balíčku

- `custom_components/hyundai_hp/` — integrace
  (`manifest.json`, `__init__.py`, `config_flow.py`, `const.py`,
  `coordinator.py`, `sensor.py`, `binary_sensor.py`, `switch.py`,
  `number.py`, `select.py`, `hacs.json`, `translations/cs.json`,
  `translations/en.json`)
- `dashboard_lovelace.yaml` — 2 záložky (Vybrané / Vše)
- `automations_example.yaml` — ukázkové automatizace
- `README_CZ.md` — tento návod
