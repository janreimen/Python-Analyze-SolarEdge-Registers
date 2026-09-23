#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analyze SolarEdge SunSpec register dumps produced by read_registers.py.

Input:
    se6000h.txt
    se16k.txt

The input files contain lines such as:

40069  0x0065  u16=   101  s16=    101
40070  0x0032  u16=    50  s16=     50
40071  0x0020  u16=    32  s16=     32

Usage:

    ./venv/bin/python3.13 analyze_sunspec.py se6000h.txt

    ./venv/bin/python3.13 analyze_sunspec.py se6000h.txt se16k.txt

Optional:

    --raw
        Also print every register belonging to every discovered model.

    --csv
        Write CSV files next to the input files.

    --all
        Same as --raw --csv
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

#
# Actual format produced by read_registers.py:
#
# 40002  0x0001  u16=     1  s16=      1
#
# Important:
# There are spaces between "u16=" and the value and between "s16=" and
# the value. Therefore the parser must use \s* after the "=".
#
REGISTER_RE = re.compile(
    r"^\s*(\d+)\s+"
    r"(0x[0-9A-Fa-f]{4})\s+"
    r"u16=\s*(-?\d+)\s+"
    r"s16=\s*(-?\d+)\s*$"
)


@dataclass
class Register:
    address: int
    raw: int
    u16: int
    s16: int


@dataclass
class Model:
    start: int
    did: int
    length: int

    @property
    def end(self) -> int:
        """
        Last register belonging to the model.

        Model header occupies:
            start       DID
            start + 1   Length

        SunSpec model payload has 'length' registers, therefore:

            last = start + length + 1
        """
        return self.start + self.length + 1

    @property
    def next_start(self) -> int:
        """
        First register of the next model.

        Two header registers + payload length.
        """
        return self.start + self.length + 2


def parse_file(filename: str) -> dict[int, Register]:
    registers: dict[int, Register] = {}

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:

            match = REGISTER_RE.match(line)

            if not match:
                continue

            address = int(match.group(1))
            raw = int(match.group(2), 16)
            u16_value = int(match.group(3))
            s16_value = int(match.group(4))

            registers[address] = Register(
                address=address,
                raw=raw,
                u16=u16_value,
                s16=s16_value,
            )

    return registers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get(
    registers: dict[int, Register],
    address: int,
) -> Register | None:
    return registers.get(address)


def u16(
    registers: dict[int, Register],
    address: int,
) -> int | None:
    r = get(registers, address)

    if r is None:
        return None

    return r.u16


def s16(
    registers: dict[int, Register],
    address: int,
) -> int | None:
    r = get(registers, address)

    if r is None:
        return None

    return r.s16


def hex_value(
    registers: dict[int, Register],
    address: int,
) -> str:

    r = get(registers, address)

    if r is None:
        return "MISSING"

    return f"0x{r.raw:04X}"


def ascii_string(
    registers: dict[int, Register],
    start: int,
    count: int,
) -> str:

    data = bytearray()

    for address in range(start, start + count):

        r = get(registers, address)

        if r is None:
            break

        data.append((r.u16 >> 8) & 0xFF)
        data.append(r.u16 & 0xFF)

    return data.decode(
        "ascii",
        errors="replace",
    ).rstrip("\x00 ")


def scale_value(
    raw: int | None,
    sf: int | None,
):
    if raw is None or sf is None:
        return None

    # SunSpec signed scale-factor NOT_IMPLEMENTED value.
    if sf == -32768:
        return None

    return raw * (10 ** sf)


def format_value(value) -> str:

    if value is None:
        return "N/A"

    if isinstance(value, float):
        return f"{value:.6g}"

    return str(value)


def combine_u32(
    registers: dict[int, Register],
    address: int,
) -> int | None:

    hi = u16(registers, address)
    lo = u16(registers, address + 1)

    if hi is None or lo is None:
        return None

    return (hi << 16) | lo


# ---------------------------------------------------------------------------
# SunSpec model discovery
# ---------------------------------------------------------------------------

def find_models(
    registers: dict[int, Register],
) -> list[Model]:

    models: list[Model] = []

    #
    # SolarEdge register notation:
    #
    #   40002 = SunSpec DID
    #   40003 = SunSpec Length
    #
    start = 40002

    while True:

        did = u16(registers, start)
        length = u16(registers, start + 1)

        if did is None or length is None:
            break

        # SunSpec end marker.
        if did == 0xFFFF:
            break

        # Clearly invalid / truncated data.
        if did == 0 or length == 0 or length > 1000:
            break

        model = Model(
            start=start,
            did=did,
            length=length,
        )

        models.append(model)

        next_start = model.next_start

        # If the next header isn't present, the file is truncated.
        if next_start not in registers:
            break

        start = next_start

    return models


# ---------------------------------------------------------------------------
# Model names
# ---------------------------------------------------------------------------

MODEL_NAMES = {
    1: "Common",
    101: "Inverter - Single Phase",
    102: "Inverter - Split Phase",
    103: "Inverter - Three Phase",
    201: "Meter - Single Phase",
    202: "Meter - Split Phase",
    203: "Meter - Wye Three Phase",
    204: "Meter - Delta Three Phase",
    701: "DER AC Measurement",
    702: "DER Capacity",
    703: "DER Settings",
    704: "DER Status",
    705: "DER AC Controls",
    706: "DER DC Measurement",
}


def model_name(did: int) -> str:
    return MODEL_NAMES.get(
        did,
        "Unknown",
    )


# ---------------------------------------------------------------------------
# Common model
# ---------------------------------------------------------------------------

def common_fields(
    registers: dict[int, Register],
    model: Model,
) -> list[tuple[int, str, str, str]]:

    start = model.start

    fields = [
        (
            start,
            "C_SunSpec_DID",
            str(u16(registers, start)),
            "uint16",
        ),
        (
            start + 1,
            "C_SunSpec_Length",
            str(u16(registers, start + 1)),
            "uint16",
        ),
        (
            start + 2,
            "C_Manufacturer",
            ascii_string(
                registers,
                start + 2,
                16,
            ),
            "String(32)",
        ),
        (
            start + 18,
            "C_Model",
            ascii_string(
                registers,
                start + 18,
                16,
            ),
            "String(32)",
        ),
        (
            start + 34,
            "C_Version",
            ascii_string(
                registers,
                start + 34,
                8,
            ),
            "String(16)",
        ),
        (
            start + 42,
            "C_SerialNumber",
            ascii_string(
                registers,
                start + 42,
                16,
            ),
            "String(32)",
        ),
        (
            start + 66,
            "C_DeviceAddress",
            str(u16(registers, start + 66)),
            "uint16",
        ),
    ]

    return fields


# ---------------------------------------------------------------------------
# Standard inverter model
# ---------------------------------------------------------------------------

def inverter_fields(
    registers: dict[int, Register],
    model: Model,
) -> list[tuple[int, str, str, str]]:

    start = model.start

    fields: list[tuple[int, str, str, str]] = []

    def add(
        offset: int,
        name: str,
        datatype: str,
        value: str,
    ):
        fields.append(
            (
                start + offset,
                name,
                value,
                datatype,
            )
        )

    # ---------------------------------------------------------------
    # Header
    # ---------------------------------------------------------------

    add(
        0,
        "I_SunSpec_DID",
        "uint16",
        str(u16(registers, start)),
    )

    add(
        1,
        "I_SunSpec_Length",
        "uint16",
        str(u16(registers, start + 1)),
    )

    # ---------------------------------------------------------------
    # AC Current
    # ---------------------------------------------------------------

    current = u16(registers, start + 2)
    current_a = u16(registers, start + 3)
    current_b = u16(registers, start + 4)
    current_c = u16(registers, start + 5)
    current_sf = s16(registers, start + 6)

    add(
        2,
        "I_AC_Current",
        "uint16",
        scaled_text(
            current,
            current_sf,
            "A",
        ),
    )

    add(
        3,
        "I_AC_CurrentA",
        "uint16",
        scaled_text(
            current_a,
            current_sf,
            "A",
        ),
    )

    add(
        4,
        "I_AC_CurrentB",
        "uint16",
        scaled_text(
            current_b,
            current_sf,
            "A",
        ),
    )

    add(
        5,
        "I_AC_CurrentC",
        "uint16",
        scaled_text(
            current_c,
            current_sf,
            "A",
        ),
    )

    add(
        6,
        "I_AC_Current_SF",
        "int16",
        str(current_sf),
    )

    # ---------------------------------------------------------------
    # AC Voltage
    # ---------------------------------------------------------------

    voltage_ab = u16(registers, start + 7)
    voltage_bc = u16(registers, start + 8)
    voltage_ca = u16(registers, start + 9)
    voltage_an = u16(registers, start + 10)
    voltage_bn = u16(registers, start + 11)
    voltage_cn = u16(registers, start + 12)
    voltage_sf = s16(registers, start + 13)

    add(
        7,
        "I_AC_VoltageAB",
        "uint16",
        scaled_text(
            voltage_ab,
            voltage_sf,
            "V",
        ),
    )

    add(
        8,
        "I_AC_VoltageBC",
        "uint16",
        scaled_text(
            voltage_bc,
            voltage_sf,
            "V",
        ),
    )

    add(
        9,
        "I_AC_VoltageCA",
        "uint16",
        scaled_text(
            voltage_ca,
            voltage_sf,
            "V",
        ),
    )

    add(
        10,
        "I_AC_VoltageAN",
        "uint16",
        scaled_text(
            voltage_an,
            voltage_sf,
            "V",
        ),
    )

    add(
        11,
        "I_AC_VoltageBN",
        "uint16",
        scaled_text(
            voltage_bn,
            voltage_sf,
            "V",
        ),
    )

    add(
        12,
        "I_AC_VoltageCN",
        "uint16",
        scaled_text(
            voltage_cn,
            voltage_sf,
            "V",
        ),
    )

    add(
        13,
        "I_AC_Voltage_SF",
        "int16",
        str(voltage_sf),
    )

    # ---------------------------------------------------------------
    # AC Power
    # ---------------------------------------------------------------

    power = s16(registers, start + 14)
    power_sf = s16(registers, start + 15)

    add(
        14,
        "I_AC_Power",
        "int16",
        scaled_text(
            power,
            power_sf,
            "W",
        ),
    )

    add(
        15,
        "I_AC_Power_SF",
        "int16",
        str(power_sf),
    )

    # ---------------------------------------------------------------
    # AC Frequency
    # ---------------------------------------------------------------

    frequency = u16(registers, start + 16)
    frequency_sf = s16(registers, start + 17)

    add(
        16,
        "I_AC_Frequency",
        "uint16",
        scaled_text(
            frequency,
            frequency_sf,
            "Hz",
        ),
    )

    add(
        17,
        "I_AC_Frequency_SF",
        "int16",
        str(frequency_sf),
    )

    # ---------------------------------------------------------------
    # VA
    # ---------------------------------------------------------------

    va = u16(registers, start + 18)
    va_sf = s16(registers, start + 19)

    add(
        18,
        "I_AC_VA",
        "uint16",
        scaled_text(
            va,
            va_sf,
            "VA",
        ),
    )

    add(
        19,
        "I_AC_VA_SF",
        "int16",
        str(va_sf),
    )

    # ---------------------------------------------------------------
    # VAR
    # ---------------------------------------------------------------

    var = s16(registers, start + 20)
    var_sf = s16(registers, start + 21)

    add(
        20,
        "I_AC_VAR",
        "int16",
        scaled_text(
            var,
            var_sf,
            "var",
        ),
    )

    add(
        21,
        "I_AC_VAR_SF",
        "int16",
        str(var_sf),
    )

    # ---------------------------------------------------------------
    # Power Factor
    # ---------------------------------------------------------------

    pf = s16(registers, start + 22)
    pf_sf = s16(registers, start + 23)

    add(
        22,
        "I_AC_PF",
        "int16",
        scaled_text(
            pf,
            pf_sf,
            "",
        ),
    )

    add(
        23,
        "I_AC_PF_SF",
        "int16",
        str(pf_sf),
    )

    # ---------------------------------------------------------------
    # AC Energy
    # ---------------------------------------------------------------

    energy = combine_u32(
        registers,
        start + 24,
    )

    energy_sf = s16(
        registers,
        start + 26,
    )

    add(
        24,
        "I_AC_Energy_WH",
        "acc32",
        scaled_text(
            energy,
            energy_sf,
            "Wh",
        ),
    )

    add(
        26,
        "I_AC_Energy_WH_SF",
        "int16",
        str(energy_sf),
    )

    # ---------------------------------------------------------------
    # DC Current
    # ---------------------------------------------------------------

    dc_current = u16(
        registers,
        start + 27,
    )

    dc_current_sf = s16(
        registers,
        start + 28,
    )

    add(
        27,
        "I_DC_Current",
        "uint16",
        scaled_text(
            dc_current,
            dc_current_sf,
            "A",
        ),
    )

    add(
        28,
        "I_DC_Current_SF",
        "int16",
        str(dc_current_sf),
    )

    # ---------------------------------------------------------------
    # DC Voltage
    # ---------------------------------------------------------------

    dc_voltage = u16(
        registers,
        start + 29,
    )

    dc_voltage_sf = s16(
        registers,
        start + 30,
    )

    add(
        29,
        "I_DC_Voltage",
        "uint16",
        scaled_text(
            dc_voltage,
            dc_voltage_sf,
            "V",
        ),
    )

    add(
        30,
        "I_DC_Voltage_SF",
        "int16",
        str(dc_voltage_sf),
    )

    # ---------------------------------------------------------------
    # DC Power
    # ---------------------------------------------------------------

    dc_power = s16(
        registers,
        start + 31,
    )

    dc_power_sf = s16(
        registers,
        start + 32,
    )

    add(
        31,
        "I_DC_Power",
        "int16",
        scaled_text(
            dc_power,
            dc_power_sf,
            "W",
        ),
    )

    add(
        32,
        "I_DC_Power_SF",
        "int16",
        str(dc_power_sf),
    )

    # ---------------------------------------------------------------
    # Temperature
    # ---------------------------------------------------------------

    temp_sink = s16(
        registers,
        start + 34,
    )

    temp_sf = s16(
        registers,
        start + 37,
    )

    add(
        34,
        "I_Temp_Sink",
        "int16",
        scaled_text(
            temp_sink,
            temp_sf,
            "°C",
        ),
    )

    add(
        37,
        "I_Temp_SF",
        "int16",
        str(temp_sf),
    )

    # ---------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------

    status = u16(
        registers,
        start + 38,
    )

    status_names = {
        1: "Off",
        2: "Sleeping",
        3: "Grid Monitoring",
        4: "Producing",
        5: "Producing (Throttled)",
        6: "Shutting Down",
        7: "Fault",
        8: "Standby",
    }

    status_text = status_names.get(
        status,
        "Unknown",
    )

    add(
        38,
        "I_Status",
        "enum16",
        f"{status} ({status_text})",
    )

    status_vendor = u16(
        registers,
        start + 39,
    )

    add(
        39,
        "I_Status_Vendor",
        "uint16",
        str(status_vendor),
    )

    return fields


# ---------------------------------------------------------------------------
# Scale-factor formatting
# ---------------------------------------------------------------------------

def scaled_text(
    raw: int | None,
    sf: int | None,
    unit: str,
) -> str:

    if raw is None:
        return "MISSING"

    #
    # SunSpec NOT_IMPLEMENTED / unavailable values.
    #
    if raw in (
        -32768,
        0x8000,
        0xFFFF,
    ):
        return f"{raw} (not available)"

    if sf is None:
        return str(raw)

    value = scale_value(
        raw,
        sf,
    )

    if value is None:
        return f"{raw} (N/A)"

    if unit:
        return f"{value:.6g} {unit}"

    return f"{value:.6g}"


# ---------------------------------------------------------------------------
# Generic raw model
# ---------------------------------------------------------------------------

def generic_model_fields(
    registers: dict[int, Register],
    model: Model,
) -> list[tuple[int, str, str, str]]:

    fields = []

    #
    # Include DID + Length + payload.
    #
    for address in range(
        model.start,
        model.end + 1,
    ):

        r = get(
            registers,
            address,
        )

        if r is None:

            fields.append(
                (
                    address,
                    "MISSING",
                    "",
                    "",
                )
            )

            continue

        if address == model.start:

            name = "SunSpec_DID"

        elif address == model.start + 1:

            name = "SunSpec_Length"

        else:

            name = (
                f"DATA_{address - model.start:03d}"
            )

        fields.append(
            (
                address,
                name,
                f"0x{r.raw:04X} / {r.u16} / {r.s16}",
                "raw",
            )
        )

    return fields


# ---------------------------------------------------------------------------
# Print model
# ---------------------------------------------------------------------------

def print_model(
    registers: dict[int, Register],
    model: Model,
    raw: bool = False,
):

    print()
    print("=" * 100)

    print(
        f"MODEL {model.did} - "
        f"{model_name(model.did)}"
    )

    print("=" * 100)

    print(
        f"Start={model.start}  "
        f"Length={model.length}  "
        f"End={model.end}  "
        f"Next={model.next_start}"
    )

    if model.did == 1:

        fields = common_fields(
            registers,
            model,
        )

    elif model.did in (
        101,
        102,
        103,
    ):

        fields = inverter_fields(
            registers,
            model,
        )

    else:

        fields = generic_model_fields(
            registers,
            model,
        )

    print()

    print(
        f"{'Register':>8}  "
        f"{'Field':<28}  "
        f"{'Value'}"
    )

    print("-" * 100)

    for address, name, value, datatype in fields:

        print(
            f"{address:8d}  "
            f"{name:<28}  "
            f"{value}"
        )

    #
    # For generic models, optionally print the raw data.
    #
    if raw and model.did not in (
        1,
        101,
        102,
        103,
    ):

        print()
        print("RAW REGISTER DATA")
        print("-" * 100)

        for address in range(
            model.start,
            model.end + 1,
        ):

            r = get(
                registers,
                address,
            )

            if r is None:
                continue

            print(
                f"{address:8d}  "
                f"0x{r.raw:04X}  "
                f"u16={r.u16:6d}  "
                f"s16={r.s16:7d}"
            )


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def write_csv(
    filename: str,
    registers: dict[int, Register],
    models: list[Model],
):

    path = Path(filename)

    output = path.with_suffix(
        ".sunspec.csv"
    )

    with open(
        output,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "model_did",
                "model_name",
                "model_start",
                "model_length",
                "register",
                "field",
                "value",
                "raw_hex",
                "u16",
                "s16",
            ]
        )

        for model in models:

            if model.did == 1:

                fields = common_fields(
                    registers,
                    model,
                )

            elif model.did in (
                101,
                102,
                103,
            ):

                fields = inverter_fields(
                    registers,
                    model,
                )

            else:

                fields = generic_model_fields(
                    registers,
                    model,
                )

            for address, field, value, datatype in fields:

                r = get(
                    registers,
                    address,
                )

                writer.writerow(
                    [
                        model.did,
                        model_name(model.did),
                        model.start,
                        model.length,
                        address,
                        field,
                        value,
                        (
                            ""
                            if r is None
                            else f"0x{r.raw:04X}"
                        ),
                        (
                            ""
                            if r is None
                            else r.u16
                        ),
                        (
                            ""
                            if r is None
                            else r.s16
                        ),
                    ]
                )

    print()
    print(
        f"CSV written: {output}"
    )


# ---------------------------------------------------------------------------
# File analysis
# ---------------------------------------------------------------------------

def analyze_file(
    filename: str,
    raw: bool,
    csv_output: bool,
):

    print()
    print("#" * 100)
    print(f"# FILE: {filename}")
    print("#" * 100)

    registers = parse_file(
        filename
    )

    if not registers:

        print(
            "ERROR: no register lines found"
        )

        return

    print(
        f"Loaded {len(registers)} registers: "
        f"{min(registers)} - {max(registers)}"
    )

    # ---------------------------------------------------------------
    # Basic SunSpec signature
    # ---------------------------------------------------------------

    print()
    print("SUNSPEC HEADER")
    print("-" * 100)

    for address in (
        40000,
        40001,
        40002,
        40003,
    ):

        r = get(
            registers,
            address,
        )

        if r is None:

            print(
                f"{address}: MISSING"
            )

        else:

            print(
                f"{address}: "
                f"0x{r.raw:04X} "
                f"u16={r.u16} "
                f"s16={r.s16}"
            )

    # ---------------------------------------------------------------
    # Model discovery
    # ---------------------------------------------------------------

    models = find_models(
        registers
    )

    print()
    print("MODEL CHAIN")
    print("-" * 100)

    if not models:

        print(
            "No complete SunSpec model could be identified."
        )

        print(
            "The input file may be truncated before "
            "40002 or the SunSpec alignment is wrong."
        )

        return

    for number, model in enumerate(
        models,
        1,
    ):

        complete = all(
            address in registers
            for address in range(
                model.start,
                model.end + 1,
            )
        )

        status = (
            "COMPLETE"
            if complete
            else "TRUNCATED"
        )

        print(
            f"{number:2d}. "
            f"DID={model.did:<4d} "
            f"{model_name(model.did):<30} "
            f"start={model.start:<5d} "
            f"length={model.length:<4d} "
            f"end={model.end:<5d} "
            f"next={model.next_start:<5d} "
            f"{status}"
        )

    # ---------------------------------------------------------------
    # Detailed models
    # ---------------------------------------------------------------

    for model in models:

        print_model(
            registers,
            model,
            raw=raw,
        )

    # ---------------------------------------------------------------
    # CSV
    # ---------------------------------------------------------------

    if csv_output:

        write_csv(
            filename,
            registers,
            models,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Analyze SolarEdge SunSpec register dumps "
            "created by read_registers.py"
        )
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="One or more register dump files",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help=(
            "Print complete raw data "
            "for unknown models"
        ),
    )

    parser.add_argument(
        "--csv",
        action="store_true",
        help=(
            "Create .sunspec.csv files"
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Enable --raw and --csv",
    )

    args = parser.parse_args()

    raw = (
        args.raw
        or args.all
    )

    csv_output = (
        args.csv
        or args.all
    )

    for filename in args.files:

        try:

            analyze_file(
                filename,
                raw=raw,
                csv_output=csv_output,
            )

        except FileNotFoundError:

            print(
                f"ERROR: file not found: {filename}"
            )

        except Exception as exc:

            print(
                f"ERROR processing "
                f"{filename}: {exc}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

