# rtltool.py
Tool for programming the Realtek RTL8762C SoC via the UART interface

[![hackaday.io](https://img.shields.io/badge/hackaday-io-gold.svg)](https://hackaday.io/project/182205-py-ft10)

## Installation
To obtain this tool, clone this repository.
```shell
git clone https://github.com/cyber-murmel/rtltool.git
```
The file `firmware0.bin` in [`rtl8762c` directory](rtl8762c/) is kept for the convenience of use and is not a part of this program; it was extracted from *RTL8762x MP Tool Kits(ZIP)* (v1.0.6.2), which can be downloaded from the [vendor page](https://www.realmcu.com/en/Home/Product/93cc0582-3a3f-4ea8-82ea-76c6504e478a). If the zip file is placed under that directory, this tool will read from the zip package instead.

This tool is compatible with the following versions of that zip (and newer versions, as long as `firmware0.bin` is placed under `BeeMPTool_kits_v*/BeeMPTool/Image` in the zip package):
- v1.0.5.8
- v1.0.6.2

### Python modules
This tool depends on the python modules listed in the `pyproject.toml`.
Run the following in the root of this repository to create a development environment
and install the dependencies.
```shell
poetry shell
poetry install
```

To enter the environment again, just run `poetry shell` in the root of this repository.

### Nix
Users of Nix or NixOS can simply run `nix-shell` to enter an environment with all necessary dependencies (except for vendor files).

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
    chip_id             Read Chip ID from OTP ROM (not implemented)
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
