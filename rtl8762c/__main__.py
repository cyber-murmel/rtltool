from argparse import ArgumentParser, Action, FileType, ArgumentError, ArgumentTypeError
from os import environ
from rtl8762c.rtl8762c import RTL8762C
from serial import Serial
from serial.serialutil import SerialException
from serial.tools.list_ports import comports as list_comports
from logging import debug, info, warning, error, exception
from logging import DEBUG, INFO, WARNING, ERROR
from coloredlogs import install as color_log

from . import commands


def arg_auto_int(i):
    return int(i, 0)


class AddrFilenamePairAction(Action):
    """Custom parser class for the address/filename pairs passed as arguments"""

    def __init__(self, option_strings, dest, nargs="+", **kwargs):
        super(AddrFilenamePairAction, self).__init__(
            option_strings, dest, nargs, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string=None):
        # validate pair arguments
        pairs = []
        for i in range(0, len(values), 2):
            try:
                address = arg_auto_int(values[i])
            except ValueError:
                raise ArgumentError(self, 'Address "%s" must be a number' % values[i])
            try:
                # argfile = open(values[i + 1], "rb")
                argfile_name = values[i + 1]
            except IOError as e:
                raise ArgumentError(self, e)
            except IndexError:
                raise ArgumentError(
                    self,
                    "Must be pairs of an address "
                    "and the binary filename to write there",
                )
            # pairs.append((address, argfile))
            pairs.append((address, argfile_name))

        # Sort the addresses and check for overlapping
        end = 0
        for address, argfile_name in sorted(pairs, key=lambda x: x[0]):
            with open(argfile_name, "rb") as argfile:
                argfile.seek(0, 2)  # seek to end
                size = argfile.tell()
                argfile.seek(0)
                sector_start = address & ~(RTL8762C.FLASH_SECTOR_SIZE - 1)
                sector_end = (
                    (address + size + RTL8762C.FLASH_SECTOR_SIZE - 1)
                    & ~(RTL8762C.FLASH_SECTOR_SIZE - 1)
                ) - 1
                if sector_start < end:
                    message = "Detected overlap at address: 0x%x for file: %s" % (
                        address,
                        argfile.name,
                    )
                    raise ArgumentError(self, message)
                end = sector_end
        setattr(namespace, self.dest, pairs)


def get_log_level(verbose, quiet):
    return (
        ERROR if quiet else WARNING if not verbose else INFO if 1 == verbose else DEBUG
    )  #  2 <= verbose


def parse_arguments():

    parser = ArgumentParser(
        description="rtltool.py - Tool for programming the Realtek RTL8762C SoC",
        prog="rtltool.py",
        epilog="""
            Copyright (C) 2022  marble

            This program is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program.  If not, see <https://www.gnu.org/licenses/>
        """,
    )

    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-q", "--quiet", action="store_true", help="turn off warnings"
    )
    verbosity.add_argument(
        "-v", "--verbose", action="count", help="set verbose loglevel"
    )

    parser.add_argument(
        "--port",
        "-p",
        help="Serial port device",
        default=environ.get("RTLTOOL_PORT", None),
    )

    parser.add_argument(
        "--baud",
        "-b",
        help="Serial port baud rate used when flashing/reading",
        type=arg_auto_int,
        default=environ.get("RTLTOOL_BAUD", RTL8762C.MAX_BAUD),
    )

    parser.add_argument(
        "--retries",
        "-r",
        help="Number of retries before giving up",
        type=arg_auto_int,
        default=3,
    )

    tool_commands = parser.add_subparsers(
        dest="command", help="Run rtltool.py {command} -h for additional help"
    )

    tool_commands.add_parser("read_mac", help="Read MAC address from OTP ROM")

    tool_commands.add_parser("chip_id", help="Read Chip ID from OTP ROM (not implemented)")

    parser_read_flash = tool_commands.add_parser(
        "read_flash", help="Read flash content"
    )
    parser_read_flash.add_argument("address", help="Start address", type=arg_auto_int)
    parser_read_flash.add_argument(
        "size", help="Size of region to dump", type=arg_auto_int
    )
    parser_read_flash.add_argument("filename", help="Name of binary dump")

    tool_commands.add_parser("erase_flash", help="Perform Chip Erase on SPI flash")

    parser_erase_region = tool_commands.add_parser(
        "erase_region", help="Erase a region of the flash"
    )
    parser_erase_region.add_argument(
        "address",
        help=f"Start address (must be multiple of {RTL8762C.FLASH_SECTOR_SIZE})",
        type=arg_auto_int,
    )
    parser_erase_region.add_argument(
        "size",
        help=f"Size of region to erase (must be multiple of {RTL8762C.FLASH_SECTOR_SIZE})",
        type=arg_auto_int,
    )

    parser_write_flash = tool_commands.add_parser(
        "write_flash", help="Write a binary blob to flash"
    )
    parser_write_flash.add_argument(
        "addr_filename",
        metavar="<address> <filename>",
        help="Address followed by binary filename, separated by space",
        action=AddrFilenamePairAction,
    )

    parser_verify_flash = tool_commands.add_parser(
        "verify_flash", help="Verify a binary blob against flash"
    )
    parser_verify_flash.add_argument(
        "addr_filename",
        help="Address and binary file to verify there, separated by space",
        action=AddrFilenamePairAction,
    )

    args = parser.parse_args()

    color_log(level=get_log_level(args.verbose, args.quiet))

    # internal sanity check - every command matches a module function of the same name
    for command in tool_commands.choices.keys():
        try:
            getattr(commands, command)
        except AttributeError as e:
            error(f"{command} should be a function in {commands.__name__}")
            raise e

    return args


def main():
    args = parse_arguments()
    debug(args)

    if args.port:
        ports = [args.port]
    else:
        warning("No serial port specified (--port). Trying available ports.")
        ports = [comport[0] for comport in list_comports()]

    if not ports:
        error("No ports available")
        return 1

    success = False
    for port in ports:
        info(f"Using port {port}")
        for attempt in range(args.retries):
            try:
                with Serial(port) as com, RTL8762C(com) as rtl:
                    if args.baud and args.baud != RTL8762C.DEFAULT_BAUD:
                        rtl.set_baud(args.baud)
                        if args.command:
                            command = getattr(commands, args.command)
                            command(rtl, args)
                success = True
                break
            except Exception as e:
                exception(e)
                warning(f"Failed attempt {attempt+1}/{args.retries}.")
        if success:
            break
        else:
            warning(f"{port} unsuccessful. Trying next port.")
    info("Finished")

    if success:
        return 0
    else:
        return 1


if "__main__" == __name__:
    exit(main())
