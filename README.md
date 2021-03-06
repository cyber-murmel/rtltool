# rtltool.py
Tool for programming the Realtek RTL8762C SoC

[![hackaday.io](https://img.shields.io/badge/hackaday-io-gold.svg)](https://hackaday.io/project/182205-py-ft10)

## Installation
To obtain this tool, clone this repository recursively.
```shell
git clone --recurse-submodules git@github.com:cyber-murmel/rtltool.git
```

### Python modules
This tool depends on the python modules listed in the requirements.txt. Run the following from the root of this repository.
```shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip --requirement requirements.txt
deactivate
```

### Nix
Users of Nix or NixOS can simply run `nix-shell` to enter an environment with all necessary dependencies.

## Usage
To use this tool, activate the venv or enter the Nix shell as described in [Installation](#installation).

```
usage: rtltool.py [-h] [-q | -v] [--port PORT] [--baud BAUD] [--retries RETRIES]
                  {read_mac,chip_id,read_flash,erase_flash,erase_region,write_flash,verify_flash} ...

rtltool.py - Tool for programming the Realtek RTL8762C SoC

positional arguments:
  {read_mac,chip_id,read_flash,erase_flash,erase_region,write_flash,verify_flash}
                        Run rtltool.py {command} -h for additional help
    read_mac            Read MAC address from OTP ROM
    chip_id             Read Chip ID from OTP ROM
    read_flash          Read flash content
    erase_flash         Perform Chip Erase on SPI flash
    erase_region        Erase a region of the flash
    write_flash         Write a binary blob to flash
    verify_flash        Verify a binary blob against flash

optional arguments:
  -h, --help            show this help message and exit
  -q, --quiet           turn off warnings
  -v, --verbose         set verbose loglevel
  --port PORT, -p PORT  Serial port device
  --baud BAUD, -b BAUD  Serial port baud rate used when flashing/reading
  --retries RETRIES, -r RETRIES
                        Number of retries before giving up
```
