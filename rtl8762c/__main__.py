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
                argfile = open(values[i + 1], "rb")
            except IOError as e:
                raise ArgumentError(self, e)
            except IndexError:
                raise ArgumentError(
                    self,
                    "Must be pairs of an address "
                    "and the binary filename to write there",
                )
            pairs.append((address, argfile))

        # # Sort the addresses and check for overlapping
        # end = 0
        # for address, argfile in sorted(pairs, key=lambda x: x[0]):
        #     argfile.seek(0, 2)  # seek to end
        #     size = argfile.tell()
        #     argfile.seek(0)
        #     sector_start = address & ~(ESPLoader.FLASH_SECTOR_SIZE - 1)
        #     sector_end = (
        #         (address + size + ESPLoader.FLASH_SECTOR_SIZE - 1)
        #         & ~(ESPLoader.FLASH_SECTOR_SIZE - 1)
        #     ) - 1
        #     if sector_start < end:
        #         message = "Detected overlap at address: 0x%x for file: %s" % (
        #             address,
        #             argfile.name,
        #         )
        #         raise argparse.ArgumentError(self, message)
        #     end = sector_end
        setattr(namespace, self.dest, pairs)


def get_log_level(verbose, quiet):
    return (
        ERROR if quiet else WARNING if not verbose else INFO if 1 == verbose else DEBUG
    )  #  2 <= verbose


def parse_arguments():

    parser = ArgumentParser(
        description="rtltool.py - Tool for programming the Realtek RTL8762C SoC",
        prog="rtltool.py",
        epilog="",
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

    operations = parser.add_subparsers(
        dest="operation", help="Run rtltool.py {command} -h for additional help"
    )

    operations.add_parser("read_mac", help="Read MAC address from OTP ROM")

    operations.add_parser("chip_id", help="Read Chip ID from OTP ROM")

    parser_write_flash = operations.add_parser(
        "write_flash", help="Write a binary blob to flash"
    )
    parser_write_flash.add_argument(
        "addr_filename",
        metavar="<address> <filename>",
        help="Address followed by binary filename, separated by space",
        action=AddrFilenamePairAction,
    )

    args = parser.parse_args()

    color_log(level=get_log_level(args.verbose, args.quiet))

    # internal sanity check - every operation matches a module function of the same name
    for operation in operations.choices.keys():
        try:
            getattr(commands, operation)
        except AttributeError as e:
            error(f"{operation} should be a function in {commands.__name__}")
            raise e

    return args


def main():
    args = parse_arguments()
    debug(args)

    if args.port:
        ports = [args.port]
    else:
        info("No serial port specified. Trying available ports.")
        ports = [comport[0] for comport in list_comports()]

    for port in ports:
        info(f"Using port {port}")
        success = False
        for attempt in range(args.retries):
            try:
                with Serial(port) as com, RTL8762C(com) as rtl:
                    if args.baud and args.baud != RTL8762C.DEFAULT_BAUD:
                        rtl.set_baud(args.baud)
                    pass
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


if "__main__" == __name__:
    main()
