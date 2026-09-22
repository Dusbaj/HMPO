"""Konstanty a registrová mapa pro Hyundai HPMO (Monoblok R290).

Zdroj: Hyundai_registry_MBS-H-EXT-CWRD_02MT_MBS_WF_BK-D-0525-01-EN.pdf
(viz A:\\HAI\\_extracted_manual.txt).

Adresy jsou NULOVÉ offsety holding registrů pro pymodbus
(tj. "100 (PLC: 40101)" => adresa 100). Jen holding registry,
funkce 03H čtení / 06H zápis jednoho / 10H zápis více registrů.

Tento modul nemá žádné závislosti na Home Assistantu,
takže ho lze testovat samostatně (python -m py_compile, import).
"""
from __future__ import annotations

DOMAIN = "hyundai_hp"

CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SIMPLE_MODE = "simple_mode"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 15
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 300
DEFAULT_SIMPLE_MODE = True

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "select"]

# ------------------------------------------------------------------
# Zapisovatelné řídicí registry 0-20 (03H/06H/10H)
# ------------------------------------------------------------------
REG_POWER = 0  # bitové pole napájení / režimů (viz BIT_POWER_* níže)
REG_MODE = 1  # 1=Auto, 2=Chlazení, 3=Topení
REG_T1S = 2  # žádaná teplota vody Zóna 1, °C, škálování (1)
REG_T1S2 = 3  # žádaná teplota vody Zóna 2, °C, škálování (1)
REG_TAS = 4  # žádaná teplota vzduchu, °C, škálování (2)
REG_T5S = 5  # žádaná teplota TUV, °C
REG_FUNC = 6  # bitové pole: křivky Z1 (bity 0-3), křivky Z2 (bity 4-7)
REG_FORCED_DHW = 7  # 0=neplatné, 1=vynuceně ON, 2=vynuceně OFF
REG_FORCED_TBH = 8  # dtto (el. dohřev TUV)
REG_FORCED_IBH = 9  # dtto (el. dohřev okruhu)
REG_SG_MAX = 10  # t_SG_MAX, 0-24 h
REG_PWR_DHW = 15  # napájení TUV: 0=off, 1=on (doporučeno pro řízení)
REG_PWR_Z1 = 16  # napájení Zóna 1 (teplota vody): 0=off, 1=on
REG_PWR_ROOM = 17  # napájení Z1/Z2 (teplota místnosti): 0=off, 1=on
REG_CURVE_Z1 = 18  # výběr křivky Zóna 1: 1-9 (doporučeno pro řízení)
REG_CURVE_Z2 = 19  # výběr křivky Zóna 2: 1-9
REG_SILENT_LEVEL = 20  # 0=tichý 1, 1=tichý 2, 2=boost (jen některé jednotky)

# Bity registru REG_POWER (strana 2 manuálu)
BIT_POWER_DISINFECTION = 0  # dezinfekce (legionella)
BIT_POWER_SILENT = 1  # tichý režim
BIT_POWER_SILENT_LEVEL = 2  # 0=úroveň 1, 1=úroveň 2
BIT_POWER_HOLIDAY_AWAY = 3  # jen čtení
BIT_POWER_HOLIDAY_HOME = 4  # jen čtení
BIT_POWER_ECO = 6  # ECO režim
BIT_POWER_PUMP_D = 7  # cirkulační čerpadlo TUV (pump_D)
BIT_POWER_CURVE_Z1 = 8  # ekvitermní křivka Z1 aktivní
BIT_POWER_CURVE_Z2 = 9  # ekvitermní křivka Z2 aktivní
BIT_POWER_C2_RESET = 10  # reset poruchy C2 (zápis 1)
BIT_POWER_ROOM = 12  # napájení Z1/Z2 (řízení dle teploty místnosti)
BIT_POWER_Z1 = 13  # napájení Zóna 1 (řízení dle teploty vody)
BIT_POWER_DHW = 14  # napájení TUV
BIT_POWER_Z2 = 15  # napájení Zóna 2 (řízení dle teploty vody)

# ------------------------------------------------------------------
# Provozní parametry 100-199, jen čtení (03H)
# ------------------------------------------------------------------
REG_FREQ = 100  # frekvence kompresoru, Hz
REG_OP_MODE = 101  # skutečný režim: 2=chlazení, 3=topení, 0=vypnuto
REG_FAN = 102  # otáčky ventilátoru, r/min
REG_EXV1 = 103  # otevření expanzního ventilu 1, P
REG_TW_IN = 104  # vstup vody do deskového výměníku, °C (**)
REG_TW_OUT = 105  # výstup vody z deskového výměníku, °C (**)
REG_T3 = 106  # teplota kondenzátoru, °C (**)
REG_T4 = 107  # venkovní teplota, °C (**)
REG_TP = 108  # výtlak kompresoru, °C (**)
REG_TH = 109  # sání kompresoru, °C (**)
REG_T1 = 110  # celková výstupní teplota vody, °C (**)
REG_TW2 = 111  # teplota vody Zóna 2, °C (**) — bez čidla ukazuje 25
REG_T2 = 112  # kapalina chladiva, °C (**)
REG_T2B = 113  # plyn chladiva, °C (**)
REG_TA = 114  # teplota místnosti, °C (**) — bez čidla ukazuje 25
REG_T5 = 115  # teplota zásobníku TUV, °C (**)
REG_P1 = 116  # vysoký tlak, kPa
REG_P2 = 117  # nízký tlak, kPa
REG_ODU_CURRENT = 118  # celkový proud venkovní jednotky, A
REG_ODU_VOLTAGE = 119  # celkové napětí venkovní jednotky, V
REG_TBT1 = 120  # akumulačka horní, °C (**)
REG_TBT2 = 121  # akumulačka dolní, °C (**)
REG_COMP_HOURS = 122  # motohodiny kompresoru, h
REG_CAPACITY = 123  # výkon jednotky, např. 6 = 6 kW
REG_ERROR = 124  # aktuální chyba, viz ERROR_TABLE (tabulka 1)
REG_STATUS1 = 128  # stavový bit 1 (odmrazování, alarm, ...)
REG_LOAD = 129  # výstupy zátěže (čerpadla, dohřevy)
REG_TF = 130  # teplota TF modulu desky, °C
REG_T1S_CALC_Z1 = 131  # vypočtené T1s Z1 dle křivky
REG_T1S_CALC_Z2 = 132  # vypočtené T1s Z2 dle křivky
REG_WATER_FLOW = 133  # průtok vody, protokol = skutečnost*100, m3/h
REG_ODU_LIMIT = 134  # kód omezení proudu venkovní jednotky
REG_HYD_CAP = 135  # kapacita hydraulického modulu (**)
REG_IDU_SW = 136  # SW verze vnitřního modulu (1-99)
REG_HMI_SW = 137  # SW verze drátového ovladače
REG_TARGET_FREQ = 138  # cílová frekvence, Hz
REG_DC_CURRENT = 139  # DC proud, protokol = skutečnost*10, A
REG_DC_VOLTAGE = 140  # DC napětí, protokol = skutečnost/10, V
REG_T1S_CALC2_Z2 = 141  # vypočtené T1s Z2 dle křivky (**) — duplicitní údaj
REG_TSOLAR = 142  # teplota solárního panelu, °C
REG_SLAVE_STATUS = 143  # online status slave jednotek 1-15 (bity)
REG_ENERGY_HI = 148  # vyšší bity kumulované spotřeby (R290 *100, kWh)
REG_ENERGY_LO = 149  # nižší bity kumulované spotřeby
REG_POWER_OUT_HI = 150  # vyšší bity výkonu (skutečnost*100, kW)
REG_POWER_OUT_LO = 151  # nižší bity výkonu
# Kumulované energie topení/chlazení/TUV (R290: protokol = skutečnost*100):
REG_HEAT_EN_HI = 148  # vyšší bity kumulované energie topení
REG_HEAT_EN_LO = 149  # nižší bity
REG_HEAT_REN_HI = 150  # vyšší bity obnovitelné energie topení
REG_HEAT_REN_LO = 151  # nižší bity
REG_HEAT_CONS_HI = 152  # vyšší bity spotřeby pro topení
REG_HEAT_CONS_LO = 153  # nižší bity
REG_HEAT_COP = 154  # kumulované COP topení (*100)
REG_COOL_EN_HI = 155  # vyšší bity energie chlazení
REG_COOL_EN_LO = 156  # nižší bity
REG_COOL_REN_HI = 157  # vyšší bity obnovitelné energie chlazení
REG_COOL_REN_LO = 158  # nižší bity
REG_COOL_CONS_HI = 159  # vyšší bity spotřeby pro chlazení
REG_COOL_CONS_LO = 160  # nižší bity
REG_COOL_EER = 161  # kumulované EER chlazení (*100)
REG_DHW_EN_HI = 162  # vyšší bity energie ohřevu TUV
REG_DHW_EN_LO = 163  # nižší bity
REG_DHW_REN_HI = 164  # vyšší bity obnovitelné energie TUV
REG_DHW_REN_LO = 165  # nižší bity
REG_DHW_CONS_HI = 166  # vyšší bity spotřeby pro TUV
REG_DHW_CONS_LO = 167  # nižší bity
REG_DHW_COP = 168  # kumulované COP ohřevu TUV (*100)
REG_COOL_CAP_RT = 169  # okamžitý výkon chlazení (skutečnost*100, kW)
REG_COOL_REN_RT = 170  # okamžitý obnovitelný výkon chlazení
REG_COOL_PWR_RT = 171  # okamžitá spotřeba chlazení
REG_COOL_EER_RT = 172  # okamžité EER chlazení (*100)
REG_DHW_CAP_RT = 173  # okamžitý výkon ohřevu TUV
REG_DHW_REN_RT = 174  # okamžitý obnovitelný výkon TUV
REG_DHW_PWR_RT = 175  # okamžitá spotřeba ohřevu TUV
REG_DHW_COP_RT = 176  # okamžité COP ohřevu TUV
REG_HEAT_CAP_RT = 177  # okamžitý výkon topení (skutečnost*100, kW)
REG_HEAT_REN_RT = 178  # okamžitý obnovitelný výkon topení
REG_HEAT_PWR_RT = 179  # okamžitá spotřeba topení
REG_HEAT_COP_RT = 180  # okamžité COP topení (*100)
REG_SYS_HEAT_HI = 181  # vyšší bity systémové energie topení (kaskáda)
REG_SYS_HEAT_LO = 182  # nižší bity
REG_SYS_REN_HI = 183  # vyšší bity systémové obnovitelné energie
REG_SYS_REN_LO = 184  # nižší bity
REG_SYS_CONS_HI = 185  # vyšší bity systémové spotřeby
REG_SYS_CONS_LO = 186  # nižší bity
REG_ERR_DETAIL = 188  # detail chyby (tabulka 2); s 124 tvoří úplný kód
# 189 = formát teplot + typ napájení (bit8: 0=1°C / 1=0,1°C; bit7: 0=1f / 1=3f)
REG_TEMP_FORMAT = 189
BIT_TEMP_PRECISION = 8  # 0 = 1 °C (neplatné 0x7F), 1 = 0,1 °C (neplatné 0x7FFF)
BIT_POWER_TYPE = 7  # 0 = 1-fázové, 1 = 3-fázové
REG_TL = 190  # teplota potrubí venkovní jednotky, °C
REG_PUMP_PWM = 191  # zpětná vazba PWM vnitřního čerpadla (*10)
REG_T9I = 192  # vstup 2. výměníku (*10, 0x7FFF=neplatné)
REG_T9O = 193  # výstup 2. výměníku (*10, 0x7FFF=neplatné)
REG_EXV2 = 194  # otevření expanzního ventilu 2, P
REG_EXV3 = 195  # otevření expanzního ventilu 3, P
REG_FAN2 = 196  # otáčky ventilátoru 2, r/min
# 198 = stavový bit 3 (povolení + provozní stavy, bity viz BIT_ST3_*)
REG_STATUS3 = 198
# 199 = provozní režim TČ: 0=vypnuto, 2=chlazení, 3=topení, 5=TUV
REG_HP_MODE = 199

# Bity REG_STATUS3 (strana 6 manuálu, čteno MSB->LSB; OVĚŘIT NAŽIVO)
BIT_ST3_TBH_EN = 15  # el. dohřev TUV povolen
BIT_ST3_AHS_EN = 14  # externí zdroj tepla povolen
BIT_ST3_T1B_EN = 12  # T1B povoleno
BIT_ST3_AHS_MODE = 11  # režim AHS: 1=topení+TUV, 0=jen topení
BIT_ST3_IBH_EN = 10  # IBH povoleno
BIT_ST3_T1_EN = 9  # T1 povoleno
BIT_ST3_METER_EN = 8  # měření energie povoleno
BIT_ST3_DHW_ON = 5  # ohřev TUV právě běží
BIT_ST3_HEAT_ON = 4  # topení právě běží
BIT_ST3_COOL_ON = 3  # chlazení právě běží

# Bity REG_STATUS1 (strana 3 manuálu, OVĚŘIT NAŽIVO)
BIT_ST1_EUV = 15  # 1 = volná elektřina
BIT_ST1_SG = 14  # smart-grid stav
BIT_ST1_REMOTE = 12  # dálkové ON/OFF: 1=platné
BIT_ST1_OIL = 11  # návrat oleje
BIT_ST1_ANTIFREEZE = 10  # protimrazová ochrana
BIT_ST1_DEFROST = 9  # odmrazování
BIT_ST1_AHS = 6  # pomocný zdroj tepla
BIT_ST1_ALARM = 4  # alarm
BIT_ST1_PUMP_S = 3  # solární čerpadlo
BIT_ST1_CRANK = 2  # ohřev klikové skříně
BIT_ST1_SV3 = 1  # ventil SV3

# Bity REG_LOAD (strana 3-4 manuálu)
BIT_LOAD_PUMP_C = 8  # směšovací čerpadlo Zóna 2
BIT_LOAD_PUMP_D = 7  # cirkulační čerpadlo TUV
BIT_LOAD_PUMP_O = 6  # externí oběhové čerpadlo
BIT_LOAD_SV2 = 5  # ventil SV2
BIT_LOAD_SV1 = 4  # ventil SV1
BIT_LOAD_PUMP_I = 3  # vnitřní oběhové čerpadlo
BIT_LOAD_TBH = 2  # el. dohřev TBH (TUV)
BIT_LOAD_IBH2 = 1  # el. dohřev IBH2
BIT_LOAD_IBH1 = 0  # el. dohřev IBH1

# ------------------------------------------------------------------
# Limity 200-208, jen čtení (03H)
# ------------------------------------------------------------------
REG_LIM_T1C_HI = 201  # horní limit T1s chlazení (protokol = skutečnost*2)
REG_LIM_T1C_LO = 202  # dolní limit T1s chlazení
REG_LIM_T1H_HI = 203  # horní limit T1s topení
REG_LIM_T1H_LO = 204  # dolní limit T1s topení
REG_LIM_TA_HI = 205  # horní limit Tas
REG_LIM_TA_LO = 206  # dolní limit Tas
REG_LIM_T5_HI = 207  # horní limit T5s
REG_LIM_T5_LO = 208  # dolní limit T5s
REG_PUMP_D_TIME = 209  # doba běhu pump_D, 5-120 min, výchozí 5

# Záložní limity, pokud jednotka limity nehlásí (ověřit dle instalačního návodu)
FALLBACK_T1S_MIN = 25.0
FALLBACK_T1S_MAX = 60.0
FALLBACK_T5S_MIN = 30.0
FALLBACK_T5S_MAX = 75.0
FALLBACK_TAS_MIN = 10.0
FALLBACK_TAS_MAX = 30.0

# ------------------------------------------------------------------
# Mapování režimů
# ------------------------------------------------------------------
# REG_MODE (zápis): 1=Auto, 2=Chlazení, 3=Topení
SET_MODE_OPTIONS = ["auto", "cool", "heat"]
SET_MODE_TO_REG = {"auto": 1, "cool": 2, "heat": 3}
SET_MODE_FROM_REG = {1: "auto", 2: "cool", 3: "heat"}

# REG_OP_MODE (čtení 101): 0=vypnuto, 2=chlazení, 3=topení
OP_MODE_MAP = {0: "off", 2: "cooling", 3: "heating"}

# REG_HP_MODE (čtení 199): 0=vypnuto, 2=chlazení, 3=topení, 5=TUV
HP_MODE_MAP = {0: "off", 2: "cooling", 3: "heating", 5: "dhw"}

SILENT_LEVEL_OPTIONS = ["level_1", "level_2", "boost"]
SILENT_LEVEL_TO_REG = {"level_1": 0, "level_2": 1, "boost": 2}
SILENT_LEVEL_FROM_REG = {0: "level_1", 1: "level_2", 2: "boost"}

FORCED_OPTIONS = ["invalid", "forced_on", "forced_off"]
FORCED_TO_REG = {"invalid": 0, "forced_on": 1, "forced_off": 2}
FORCED_FROM_REG = {0: "invalid", 1: "forced_on", 2: "forced_off"}

# Křivky 1-9
CURVE_OPTIONS = [str(i) for i in range(1, 10)]

# ------------------------------------------------------------------
# Tabulka chyb 1 (registr 124): hodnota -> (kód, popis EN, popis CZ)
# ------------------------------------------------------------------
ERROR_TABLE = {
    1: ("E0", "Water flow fault (E8 shown 3 times)", "Porucha průtoku vody (3x E8)"),
    2: ("E1", "Power supply phase fault", "Porucha fáze napájení"),
    3: ("E2", "Controller - hydraulic module comm fault", "Porucha komunikace ovladač - hydraulický modul"),
    4: ("E3", "Final outlet water temp sensor (T1) fault", "Porucha čidla výstupní teploty vody (T1)"),
    5: ("E4", "Water tank temp sensor (T5) fault", "Porucha čidla teploty zásobníku (T5)"),
    6: ("E5", "Condenser outlet refrigerant sensor (T3) fault", "Porucha čidla T3"),
    7: ("E6", "Ambient temp sensor (T4) fault", "Porucha čidla venkovní teploty (T4)"),
    8: ("E7", "Buffer tank top sensor (Tbt1) fault", "Porucha čidla Tbt1"),
    9: ("E8", "Water flow failure", "Ztráta průtoku vody"),
    10: ("E9", "Suction temp sensor (Th) fault", "Porucha čidla sání (Th)"),
    11: ("EA", "Discharge temp sensor (Tp) fault", "Porucha čidla výtlaku (Tp)"),
    12: ("Eb", "Solar temp sensor (Tsolar) fault", "Porucha solárního čidla (Tsolar)"),
    13: ("Ec", "Buffer tank bottom sensor (Tbt2) fault", "Porucha čidla Tbt2"),
    14: ("Ed", "Inlet water temp sensor (Tw_in) fault", "Porucha čidla vstupní vody (Tw_in)"),
    15: ("EE", "Hydraulic module EEPROM failure", "Porucha EEPROM hydraulického modulu"),
    20: ("P0", "Low pressure switch protection", "Ochrana nízkotlakého presostatu"),
    21: ("P1", "High pressure switch protection", "Ochrana vysokotlakého presostatu"),
    23: ("P3", "Compressor overcurrent protection", "Nadproudová ochrana kompresoru"),
    24: ("P4", "High discharge temperature protection", "Ochrana vysoké teploty výtlaku"),
    25: ("P5", "|Tw_out - Tw_in| too big protection", "Ochrana rozdílu teplot vody"),
    26: ("P6", "Inverter module protection", "Ochrana invertorového modulu"),
    31: ("Pb", "Anti-freeze mode", "Protimrazový režim"),
    33: ("Pd", "High condenser outlet temp protection", "Ochrana vysoké teploty kondenzátoru"),
    38: ("PP", "Tw_out - Tw_in abnormal protection", "Ochrana abnormálního rozdílu teplot"),
    39: ("H0", "Main board - hydraulic module comm fault", "Porucha komunikace desek"),
    40: ("H1", "Inverter PCB A - control PCB B comm fault", "Porucha komunikace PCB A-B"),
    41: ("H2", "Refrigerant liquid sensor (T2) fault", "Porucha čidla T2"),
    42: ("H3", "Refrigerant gas sensor (T2B) fault", "Porucha čidla T2B"),
    43: ("H4", "Three times P6 protection", "3x ochrana P6"),
    44: ("H5", "Room temp sensor (Ta) fault", "Porucha čidla místnosti (Ta)"),
    45: ("H6", "DC fan motor fault", "Porucha DC ventilátoru"),
    46: ("H7", "Voltage protection", "Napěťová ochrana"),
    47: ("H8", "Pressure sensor fault", "Porucha tlakového čidla"),
    48: ("H9", "Outlet water zone 2 sensor (Tw2) fault", "Porucha čidla Tw2"),
    49: ("HA", "Outlet water sensor (Tw_out) fault", "Porucha čidla Tw_out"),
    50: ("Hb", "3x PP protection and Tw_out<7C", "3x PP ochrana, Tw_out<7 °C"),
    52: ("Hd", "Hydraulic module parallel comm fault", "Porucha paralelní komunikace"),
    53: ("HE", "Main board - thermostat board comm error", "Porucha komunikace s termostatem"),
    54: ("HF", "Inverter module EEPROM fault", "Porucha EEPROM invertoru"),
    55: ("HH", "H6 shown 10 times in 2 hours", "10x H6 během 2 hodin"),
    57: ("HP", "Low pressure protection 3x in 1 hour", "3x nízkotlaká ochrana za hodinu"),
    65: ("C7", "Transducer module overtemperature", "Přehřátí měničového modulu"),
    112: ("bH", "PED PCB fault", "Porucha PED desky"),
    116: ("F1", "Low DC bus voltage protection", "Ochrana nízkého DC napětí"),
    134: ("L0", "Module protection", "Ochrana modulu"),
    135: ("L1", "DC bus low voltage protection", "Ochrana nízkého DC napětí"),
    136: ("L2", "DC bus high voltage protection", "Ochrana vysokého DC napětí"),
    138: ("L4", "MCE fault", "Porucha MCE"),
    139: ("L5", "Zero speed protection", "Ochrana nulových otáček"),
    141: ("L7", "Phase sequence fault", "Porucha sledu fází"),
    142: ("L8", "Speed difference front/back clock > 15 Hz", "Rozdíl otáček > 15 Hz"),
    143: ("L9", "Speed difference real/setting > 15 Hz", "Rozdíl žádaných otáček > 15 Hz"),
}

INVALID_8 = 0x7F
INVALID_16 = 0x7FFF


def is_invalid(raw: int) -> bool:
    """Neplatná hodnota teploty (bez čidla / nedostupné)."""
    return raw in (INVALID_8, INVALID_16)


def decode_p1(raw: int, tenth: bool) -> float | None:
    """Škálování (1): bit8=0 → skutečnost, bit8=1 → protokol = skutečnost*2."""
    if is_invalid(raw):
        return None
    return round(raw / 2.0, 1) if tenth else float(raw)


def decode_p2(raw: int, tenth: bool) -> float | None:
    """Škálování (2): bit8=0 → skutečnost, bit8=1 → protokol = skutečnost*10."""
    if is_invalid(raw):
        return None
    return round(raw / 10.0, 1) if tenth else float(raw)


def decode_plain(raw: int) -> float | None:
    """Teplota bez škálování."""
    if is_invalid(raw):
        return None
    return float(raw)


def encode_p1(value: float, tenth: bool) -> int:
    """Žádaná hodnota (1) zpět do protokolu."""
    return int(round(value * 2.0)) if tenth else int(round(value))


def encode_p2(value: float, tenth: bool) -> int:
    """Žádaná hodnota (2) zpět do protokolu."""
    return int(round(value * 10.0)) if tenth else int(round(value))


def combine_32(high: int, low: int) -> int:
    """Složení 32bit hodnoty ze dvou registrů (vyšší + nižší bity)."""
    return ((high & 0xFFFF) << 16) | (low & 0xFFFF)


def energy_kwh(high: int, low: int) -> float:
    """Kumulovaná energie R290: protokol = skutečnost*100 → kWh."""
    return round(combine_32(high, low) / 100.0, 2)


def scale_100(raw: int) -> float:
    """Okamžitý výkon / COP / EER: protokol = skutečnost*100."""
    return round(raw / 100.0, 2)
