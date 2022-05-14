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
    @abstractmethod
    def bytecode(self):
        pass

    @property
    @abstractmethod
    def response_len(self):
        pass

    @property
    def process_response(self, response):
        pass

    def _expect(self, expected, actual):
        if expected != actual:
            warning("Received bytes mismatch expected bytes")
            warning("Expected {}".format(expected.hex()))
            warning("Received {}".format(actual.hex()))
            warning("Reset device into flash mode or try lower baud rate.")
            raise ExpectError("Received bytes mismatch expected bytes")


class write_fw0(Operation):
    def __init__(self, chunk, frame_number):
        self._bytecode = b"\x01\x20\xFC"
        self._bytecode += pack("BB", len(chunk) + 1, frame_number)
        self._bytecode += chunk
        self._response = b"\x04\x0E\x05\x02\x20\xFC\x00"
        self._response += pack("B", frame_number)

    @property
    def bytecode(self):
        return self._bytecode

    @property
    def response_len(self):
        return len(self._response)

    def process_response(self, response):
        self._expect(self._response, response)


class system_report(Operation):
    @property
    def bytecode(self):
        return b"\x01\x62\xFC\x09\x20\x34\x12\x20\x00\x31\x38\x20\x00"

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


class set_baud(Operation):
    def __init__(self, baud_rate):
        self._bytecode = b"\x87\x10\x10"
        self._bytecode += pack("<I", baud_rate)
        self._bytecode += b"\xff"
        self._bytecode += pack("<H", CrcArc.calc(bytearray(self._bytecode)))
        self._response = b"\x87\x10\x10\x00\x00\x00\x00\x00\x5A\xD7"

    @property
    def bytecode(self):
        return self._bytecode

    @property
    def response_len(self):
        return len(self._response)

    def process_response(self, response):
        self._expect(self._response, response)
