#!/usr/bin/env python3

import sys
from pymodbus.client import ModbusTcpClient

HOST = sys.argv[1]
PORT = int(sys.argv[2])
DEVICE_ID = int(sys.argv[3])

START_REGISTER = 40002
END_REGISTER = 40551

# Must be <= 125 for Modbus Read Holding Registers.
# 120 leaves a little margin and works reliably.
CHUNK_SIZE = 120

client = ModbusTcpClient(
    HOST,
    port=PORT,
    timeout=5,
)

if not client.connect():
    print("Connection failed")
    sys.exit(1)

print(f"Connected to {HOST}:{PORT}, device-id={DEVICE_ID}")
print()

try:
    current = START_REGISTER

    while current <= END_REGISTER:

        count = min(
            CHUNK_SIZE,
            END_REGISTER - current + 1,
        )

        # SolarEdge register -> zero-based Modbus PDU address.
        pdu_address = current - 40000

        result = client.read_holding_registers(
            address=pdu_address,
            count=count,
            device_id=DEVICE_ID,
        )

        if result.isError():
            print(
                f"Modbus error at "
                f"SolarEdge register {current}, "
                f"PDU address {pdu_address}:"
            )
            print(result)
            sys.exit(1)

        for offset, value in enumerate(result.registers):

            register = current + offset

            unsigned = value
            signed = (
                value
                if value < 32768
                else value - 65536
            )

            print(
                f"{register:5d}  "
                f"0x{value:04X}  "
                f"u16={unsigned:6d}  "
                f"s16={signed:7d}"
            )

        current += count

finally:
    client.close()
