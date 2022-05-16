from logging import debug, info, warning, error
from enum import Enum
from time import sleep
from struct import pack, unpack
from os.path import dirname, abspath, join as pathcat
from zipfile import ZipFile
from . import operations

_PKG_DIR = dirname(abspath(__file__))


class RTL8762C:
    DEFAULT_BAUD = 115200
    MAX_BAUD = 921600
    _RESET_PULSE_WIDTH = 0.01
    _BOOT_MODE_SUSTAIN = 0.5
    _BAUD_CHANGE_DELAY = 0.4
    _TOOL_PATH = "tools/RTL_Tools/Bee2MPTool_kits_v1.0.4.0.zip"
    _FW0_PATH = "Bee2MPTool_kits_v1.0.4.0/Bee2MPTool/Image/firmware0.bin"
    _FW0_CHUNK_SIZE = 252
    _FLASH_START = 0x00800000
    FLASH_SECTOR_SIZE = 0x1000  # 4 kiB
    _FLASH_ADDR_MAC = 0x00801409
    _state = None

    class ModuleState(Enum):
        RESET = 0
        FLASH = 1
        RUN = 2

    def __init__(self, com):
        self._com = com
        # configure UART
        self._com.baudrate = self.DEFAULT_BAUD
        self._com.bytesize = 8
        self._com.parity = "N"
        self._com.stopbits = 1
        self._com.timeout = 2
        # bring into inactive reset state
        self._assert_state(self.ModuleState.RESET)

    def __enter__(self):
        self._assert_state(self.ModuleState.FLASH)
        return self

    def __exit__(self, type, value, traceback):
        self._assert_state(self.ModuleState.RUN)

    def _transmit(self, data):
        self._com.write(data)
        self._com.flush()
        debug("tx: {:32s}".format(data.hex()))

    def _receive(self, length):
        data = self._com.read(length)
        debug("rx: {:32s}".format(data.hex()))
        return data

    def _exec(self, operation):
        self._transmit(operation.bytecode)
        response = self._receive(operation.response_len)
        return operation.process_response(response)

    def _write_fw0(self):
        debug("Starting Transmission of firmware0")
        with ZipFile(
            pathcat(_PKG_DIR, self._TOOL_PATH), "r"
        ) as tool_archive, tool_archive.open(self._FW0_PATH, "r") as fw0:
            frame_number = 0
            while True:
                chunk = fw0.read(self._FW0_CHUNK_SIZE)
                if not chunk:
                    break
                self._exec(operations.write_fw0(chunk, frame_number))
                frame_number += 1
        debug("Transmission of firmware0 Finished")

    def _assert_state(self, state):
        # if state doesn't change, exit
        if self._state == state:
            return

        debug("Starting State Change")

        # set RESET pin low
        self._com.rts = True

        sleep(self._RESET_PULSE_WIDTH)

        if self.ModuleState.RESET == state:
            # keep in reset
            return
        elif self.ModuleState.FLASH == state:
            # set LOG pin low
            self._com.dtr = True
            self._com.baud = self.DEFAULT_BAUD

        elif self.ModuleState.RUN == state:
            # set LOG pin high
            self._com.dtr = False

        # set RESET pin high
        self._com.rts = False
        sleep(self._BOOT_MODE_SUSTAIN)

        # set LOG pin high
        self._com.dtr = False
        sleep(self._BAUD_CHANGE_DELAY)

        if self.ModuleState.FLASH == state:
            info("## Performing Handshake")
            # self._exec(self._COMMANDS.open)
            #     self._init_flash_mode()
            info("## Writing firmware0")
            self._write_fw0()
            #     info("## Performing Magic Sequence")
            #     self._unknown_sequence()
            report = self._exec(operations.system_report())
            self._flash_size = report["flash_size"]
            info(f"Flash Size: {self._flash_size//1024} kiB")

        self._state = state

        debug("State Change Finished")

    def set_baud(self, baud_rate):
        self._exec(operations.set_baud(baud_rate))
        self._com.baudrate = baud_rate
        # sleep(self._BAUD_CHANGE_DELAY)

    def read_mac(self):
        reverse_mac = self._exec(operations.read_flash(self._FLASH_ADDR_MAC, 6))
        print(reverse_mac)
        return reverse_mac[::-1]
        print("foo")

    def read_flash(self, address, size):
        chunks = [
            self._exec(
                operations.read_flash(
                    address + i, min(self.FLASH_SECTOR_SIZE, size - i)
                )
            )
            for i in range(0, size, self.FLASH_SECTOR_SIZE)
        ]
        return b"".join(chunks)

    def erase_region(self, address, size):
        for i in range(0, size, self.FLASH_SECTOR_SIZE):
            self._exec(operations.erase_region(address + i, self.FLASH_SECTOR_SIZE))

    def erase_flash(self):
        if self._flash_size <= 512 * 1024:
            self._exec(operations.erase_flash())
        else:
            for i in range(0, self._flash_size, self.FLASH_SECTOR_SIZE):
                self._exec(
                    operations.erase_region(
                        self._FLASH_START + i, self.FLASH_SECTOR_SIZE
                    )
                )

    def write_flash(self, address, data):
        for i in range(0, len(data), self.FLASH_SECTOR_SIZE):
            chunk = data[i : min(i + self.FLASH_SECTOR_SIZE, len(data))]
            self.erase_region(address + i, len(chunk))
            self._exec(operations.write_flash(address + i, chunk))
            self.verify_flash(address + i, chunk)

    def verify_flash(self, address, data):
        for i in range(0, len(data), self.FLASH_SECTOR_SIZE):
            chunk = data[i : min(i + self.FLASH_SECTOR_SIZE, len(data))]
            self._exec(operations.verify_flash(address + i, chunk))
