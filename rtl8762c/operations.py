from abc import ABC, abstractmethod
from struct import pack, unpack
from logging import debug, info, warning, error
from crccheck.crc import CrcArc


class CRCError(Exception):
    pass


class ExpectError(Exception):
    pass


class Operation(ABC):
    @property
    def bytecode(self):
        return self._bytecode

    @property
    def response_len(self):
        return len(self._response)

    @property
    @abstractmethod
    def process_response(self, response):
        pass

    def _expect(self, expected, actual):
        if expected != actual:
            warning("Received bytes mismatch expected bytes")
            warning("Expected {}".format(expected.hex()))
            warning("Received {}".format(actual.hex()))
            warning("Reset device into flash mode or try lower baud rate.")
            raise ExpectError("Received bytes mismatch expected bytes")


class CRC_Operation(Operation):
    @property
    def bytecode(self):
        bytecode = self._bytecode
        bytecode += pack("<H", CrcArc.calc(bytearray(self._bytecode)))
        return bytecode

    def _check_crc(self, response):
        if 0 != CrcArc.calc(response):
            raise CRCError("CRC error")

    def process_response(self, response):
        self._check_crc(response)
        self._expect(self._response, response)


class write_fw0(Operation):
    def __init__(self, chunk, frame_number):
        self._bytecode = b"\x01\x20\xFC"
        self._bytecode += pack("BB", len(chunk) + 1, frame_number)
        self._bytecode += chunk
        self._response = b"\x04\x0E\x05\x02\x20\xFC\x00"
        self._response += pack("B", frame_number)

    def process_response(self, response):
        self._expect(self._response, response)


class system_report(Operation):
    _bytecode = b"\x01\x62\xFC\x09\x20\x34\x12\x20\x00\x31\x38\x20\x00"

    @property
    def response_len(self):
        return 77

    def process_response(self, response):
        report = response[7:]
        if 0 != CrcArc.calc(report):
            raise CRCError("CRC error")
        head = report[:3]
        flash_addr = report[17:21]
        flash_size = report[21:25]
        report_dict = {
            "flash_addr": unpack(">I", flash_addr)[0],
            "flash_size": unpack(">I", flash_size)[0],
        }
        return report_dict


class set_baud(CRC_Operation):
    _response = b"\x87\x10\x10\x00\x00\x00\x00\x00\x5A\xD7"

    def __init__(self, baud_rate):
        self._bytecode = b"\x87\x10\x10"
        self._bytecode += pack("<I", baud_rate)
        self._bytecode += b"\xff"


class read_flash(CRC_Operation):
    def __init__(self, address, size):
        self._bytecode = b"\x87\x33\x10"
        self._bytecode += pack("<I", address)
        self._bytecode += pack("<I", size)
        self._size = size

    @property
    def response_len(self):
        return self._size + 10

    def process_response(self, response):
        assert self.response_len == len(response), "Didn't read enough bytes!"
        self._check_crc(response)
        return response[8:-2]


class erase_region(CRC_Operation):
    _response = b"\x87\x30\x10\x00\x00\x00\x00\x00\x7B\x15"

    def __init__(self, address, size):
        self._bytecode = b"\x87\x30\x10"
        self._bytecode += pack("<I", address)
        self._bytecode += pack("<I", size)


class erase_flash(CRC_Operation):
    _response = b"\x87\x31\x10\x00\x00\x00\x00\x00\x6B\xD5"
    _bytecode = b"\x87\x31\x10"


class write_flash(CRC_Operation):
    _response = b"\x87\x32\x10\x00\x00\x00\x00\x00\x58\xD5"

    def __init__(self, address, chunk):
        self._bytecode = b"\x87\x32\x10"
        self._bytecode += pack("<I", address)
        self._bytecode += pack("<I", len(chunk))
        self._bytecode += chunk


class verify_flash(CRC_Operation):
    _response = b"\x87\x50\x10\x00\x00\x00\x00\x00\x1B\x13"

    def __init__(self, address, chunk):
        self._bytecode = b"\x87\x50\x10"
        self._bytecode += pack("<I", address)
        self._bytecode += pack("<I", len(chunk))
        self._bytecode += pack("<H", CrcArc.calc(chunk))
