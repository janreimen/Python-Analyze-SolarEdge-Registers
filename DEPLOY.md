Deployment Guide

Python Analyze SolarEdge Registers

This document describes how to install and run the SolarEdge register analyzer on a Linux system.

The procedure creates an isolated Python virtual environment so that the project does not interfere with the system Python installation or other SolarEdge/Domoticz software.

---

1. Requirements

A Linux system with:

- Python 3.10+
- "python3-venv"
- Git
- network access to the SolarEdge inverter
- SolarEdge Modbus TCP enabled

The inverter must be reachable on TCP port:

1502

---

2. Install System Packages

On Debian/Raspberry Pi OS:

sudo apt update
sudo apt install -y git python3 python3-venv

Check Python:

python3 --version

---

3. Clone the Repository

Using the GitHub SSH repository:

cd /srv
git clone git@github.com:janreimen/Python-Analyze-SolarEdge-Registers.git
cd Python-Analyze-SolarEdge-Registers

Alternatively, using HTTPS:

cd /srv
git clone https://github.com/janreimen/Python-Analyze-SolarEdge-Registers.git
cd Python-Analyze-SolarEdge-Registers

---

4. Create the Virtual Environment

Create a dedicated virtual environment inside the project:

python3 -m venv venv

Activate it:

source venv/bin/activate

The shell prompt should now indicate the environment, for example:

(venv) pi@rpi4dmz:/srv/Python-Analyze-SolarEdge-Registers$

---

5. Install Python Dependencies

Upgrade pip:

python -m pip install --upgrade pip

Install the project dependencies:

python -m pip install -r requirements.txt

The project currently requires:

pymodbus==3.15.0

---

6. Verify the Installation

Check the PyModbus version:

python -c "import pymodbus; print(pymodbus.__version__)"

Check the scripts:

python read_registers.py

python analyze_sunspec.py

The scripts should start without a Python import error.

---

7. Test the SolarEdge Connection

Example:

python read_registers.py 192.168.0.100 1502 1

If the connection is successful, the output starts with something similar to:

Connected to 192.168.0.100:1502, device-id=1

The subsequent lines contain the raw registers.

---

8. Generate a Register Dump

Save the complete output to a text file:

python read_registers.py 192.168.0.100 1502 1 > se6000h.txt

For another inverter:

python read_registers.py 192.168.0.100 1502 3 > se16k.txt

Check the dump:

wc -l se6000h.txt

The standard configured range contains 550 registers.

Therefore the file normally contains:

552 lines

Two additional lines contain the connection/header information.

---

9. Analyze a Register Dump

Run the standard analyzer:

python analyze_sunspec.py se6000h.txt

For the complete model and field analysis:

python analyze_sunspec.py --all se6000h.txt

Save the result:

python analyze_sunspec.py --all se6000h.txt > se6000h_analysis.txt

For the SE16K:

python analyze_sunspec.py --all se16k.txt > se16k_analysis.txt

---

10. Generate CSV Output

For spreadsheet analysis:

python analyze_sunspec.py --csv se6000h.txt

Or save it explicitly:

python analyze_sunspec.py --csv se6000h.txt > se6000h.csv

---

11. Deactivate the Virtual Environment

When finished:

deactivate

To use the project again:

cd /srv/Python-Analyze-SolarEdge-Registers
source venv/bin/activate

---

12. Updating the Project

Pull the latest repository version:

cd /srv/Python-Analyze-SolarEdge-Registers
git pull

If dependencies have changed:

source venv/bin/activate
python -m pip install -r requirements.txt

---

13. Updating PyModbus

The dependency is intentionally restricted to the PyModbus 3.x series.

To update to the newest compatible version:

source venv/bin/activate
python -m pip install --upgrade "pymodbus==3.15.0"

Verify:

python -c "import pymodbus; print(pymodbus.__version__)"

---

14. No "solaredge_modbus" Dependency

This project does not require:

solaredge_modbus

The register reader communicates directly with the inverter through:

PyModbus
    |
    v
Modbus TCP
    |
    v
SolarEdge inverter

Keeping this environment independent prevents another SolarEdge library from changing or obscuring the behavior being tested.

---

15. Network Troubleshooting

Check basic connectivity:

ping 192.168.0.100

Check whether TCP port 1502 is reachable:

nc -vz 192.168.0.100 1502

For the second inverter:

nc -vz 192.168.0.101 1502

A successful result should indicate that TCP port "1502" is open.

If TCP connectivity works but the Python reader cannot read registers, check:

- SolarEdge Modbus TCP configuration
- inverter IP address
- TCP port
- SunSpec/Modbus configuration
- device ID
- firewall rules
- inverter firmware/configuration

---

16. Example: Complete SE6000H Session

cd /srv/Python-Analyze-SolarEdge-Registers

source venv/bin/activate

python read_registers.py 192.168.0.100 1502 1 > se6000h.txt

wc -l se6000h.txt

python analyze_sunspec.py --all se6000h.txt > se6000h_analysis.txt

less se6000h_analysis.txt

---

17. Example: Complete SE16K Session

cd /srv/Python-Analyze-SolarEdge-Registers

source venv/bin/activate

python read_registers.py 192.168.0.101 1502 3 > se16k.txt

wc -l se16k.txt

python analyze_sunspec.py --all se16k.txt > se16k_analysis.txt

less se16k_analysis.txt

---

18. Git Repository Maintenance

Check the working tree:

git status

Do not normally add live register dumps:

se6000h.txt
se6000h_analysis.txt
se16k.txt
se16k_analysis.txt
*.csv

The repository should contain the source code and documentation, not live inverter data.

Check tracked files:

git ls-files

Expected core files:

.gitignore
DEPLOY.md
README.md
analyze_sunspec.py
read_registers.py
requirements.txt

---

19. Release v0.1.0

The initial release is:

v0.1.0

Create the tag:

git tag -a v0.1.0 -m "Release v0.1.0"

Push the branch:

git push -u origin master

Push the release tag:

git push origin v0.1.0

Verify:

git tag
git log --oneline --decorate -3

The repository is then ready for use as the standalone SolarEdge register-analysis tool.
