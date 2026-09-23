Python Analyze SolarEdge Registers

A lightweight Python toolkit for reading and analyzing SolarEdge SunSpec Modbus TCP registers.

The project is intended as a standalone diagnostic and development tool for inspecting the register layout and live values of SolarEdge inverters. It can be used to establish an accurate register map before implementing or debugging integrations such as Domoticz plugins.

Features

- Read SolarEdge holding registers over Modbus TCP.
- Automatically handle Modbus register-read limits by reading in chunks.
- Save complete raw register dumps for later analysis.
- Discover SunSpec models from the register map.
- Decode common SunSpec models.
- Decode inverter model registers.
- Display:
  - SolarEdge register address
  - raw hexadecimal value
  - unsigned 16-bit value
  - signed 16-bit value
  - SunSpec field name
  - datatype
  - scale factor
  - decoded value
- Export analysis to CSV.
- No dependency on Domoticz.
- No dependency on the "solaredge_modbus" package.

Requirements

- Python 3.10 or newer
- A SolarEdge inverter with Modbus TCP enabled
- Network access to the inverter's Modbus TCP port
- PyModbus

The default SolarEdge Modbus TCP port is:

1502

Installation

Clone the repository:

* git clone git@github.com:janreimen/Python-Analyze-SolarEdge-Registers.git
* cd Python-Analyze-SolarEdge-Registers

Create a virtual environment:

* python3 -m venv venv

Activate it:

* source venv/bin/activate

Install the dependencies:

* python -m pip install --upgrade pip
* pip install -r requirements.txt

Verify PyModbus:

* python -c "import pymodbus; print(pymodbus.__version__)"

Reading Registers

The "read_registers.py" script reads the SolarEdge register range and produces a plain-text dump.

Example for a SolarEdge SE6000H (Modbus Master : id 1):

* python read_registers.py 192.168.0.100 1502 1 > se6000h.txt

Example for a SolarEdge SE16K (Modbus Follower : id 3):

* python read_registers.py 192.168.0.101 1502 3 > se16k.txt

The arguments are:

* read_registers.py <IP> <PORT> <DEVICE_ID>

For example:

IP         = 192.168.0.100
PORT       = 1502
DEVICE_ID  = 1

Register Addressing

SolarEdge/SunSpec registers are presented using addresses such as:

40002
40003
40004
...

PyModbus uses the corresponding zero-based PDU address.

For this project:

SolarEdge register 40000 = PDU address 0

Therefore:

PDU address = SolarEdge register - 40000

For example:

SolarEdge register 40002
PDU address            2

The scripts perform this conversion automatically.

Modbus Read Size

Modbus Read Holding Registers requests are limited to a maximum of 125 registers.

The reader therefore uses smaller chunks instead of attempting to request the complete register range in a single operation.

This avoids errors such as:

ValueError: 1 <= count 500 <= 125 !

Raw Register Dump

A raw dump looks like this:

40002  0x0001  u16=     1  s16=      1
40003  0x0041  u16=    65  s16=     65
40004  0x536F  u16= 21359  s16=  21359

The columns are:

SolarEdge register
Hexadecimal value
Unsigned 16-bit value
Signed 16-bit value

The raw dump is deliberately kept simple so that it can also be inspected with standard Unix tools.

Analyzing a Register Dump

Run the analyzer against a previously generated dump:

python analyze_sunspec.py se6000h.txt

For the complete analysis:

python analyze_sunspec.py --all se6000h.txt

Save the analysis:

python analyze_sunspec.py --all se6000h.txt > se6000h_analysis.txt

For the SE16K:

python analyze_sunspec.py --all se16k.txt > se16k_analysis.txt

CSV Output

CSV output can be generated with:

python analyze_sunspec.py --csv se6000h.txt

This is useful for further analysis with LibreOffice, Excel, Python, or other data-processing tools.

SunSpec Models

The analyzer identifies SunSpec models by their:

DID
Length
Start register
End register

For example, a typical inverter map begins with:

40002  DID 1

The Common model contains the inverter identification information.

The next model begins after the Common model's payload.

For an inverter model:

40069  DID 101/103
40070  Model length

The exact models present depend on the inverter firmware and configuration.

The analyzer therefore discovers the model boundaries from the live register data rather than assuming that every inverter has exactly the same model layout.

Scale Factors

SunSpec values frequently use a separate signed scale factor.

The physical value is generally calculated as:

physical_value = raw_value × 10^scale_factor

For example:

raw value      = 2290
scale factor   = -1

2290 × 10^-1
= 229.0

The analyzer reports both the raw register value and the decoded/scaled value where the field definition is known.

Example Workflow

A typical diagnostic session is:

# Read the inverter
python read_registers.py 192.168.0.100 1502 1 > se6000h.txt

# Analyze the complete dump
python analyze_sunspec.py --all se6000h.txt > se6000h_analysis.txt

# Inspect the result
less se6000h_analysis.txt

For another inverter:

* python read_registers.py 192.168.0.101 1502 3 > se16k.txt
* python analyze_sunspec.py --all se16k.txt > se16k_analysis.txt

Keeping Raw Dumps Out of Git

Live inverter dumps should normally not be committed to the repository.

They can contain device-specific information such as:

- inverter serial number
- device address
- firmware information
- live operating values

The supplied ".gitignore" excludes generated ".txt" and ".csv" files while keeping:

README.md
DEPLOY.md

tracked.

Relationship to Domoticz

This project is intentionally independent of Domoticz.

Its purpose is to establish a trustworthy register map first.

The resulting information can then be used to verify or develop a SolarEdge integration, for example:

SolarEdge inverter
        |
        | Modbus TCP
        v
Python Analyze SolarEdge Registers
        |
        | register / field verification
        v
Domoticz-SolarEdge integration

This separation makes it possible to determine whether a problem is caused by:

- the inverter register map
- SunSpec model interpretation
- scale factors
- Modbus communication
- or the integration itself.

Project Status

Version:

v0.1.0

This release provides the initial standalone register-reading and SunSpec-analysis toolkit.

License

See the repository for the applicable license.
