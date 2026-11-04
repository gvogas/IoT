import threading
import time

from config import RFID_BAUD, RFID_PORT

try:
    import serial
except ImportError:
    serial = None

# Chafon "inventory" command: asks the reader for the tags it can see right now
READ_TAGS = bytes([0x04, 0xFF, 0x01, 0x1B, 0xB4])

# How long to wait for the reader to answer after the command
REPLY_WAIT = 0.5

# The reader is one serial port, so only one request can talk to it at a time
_lock = threading.Lock()
_port = None
_leftover = b""


class ReaderError(Exception):
    pass


# Pull EPCs out of CF600 tag frames
# Frame: CF | addr | cmd(2) | len | status | rssi(2) | ant | ? | epc_len | epc | crc(2)
# Gives back (list of EPC hex strings, leftover bytes of an incomplete frame)
def parse_epcs(buf):
    epcs = []
    i = 0
    while True:
        i = buf.find(0xCF, i)
        if i < 0 or i + 5 > len(buf):
            return epcs, buf[i:] if i >= 0 else b""
        length = buf[i + 4]
        end = i + 5 + length + 2
        if end > len(buf):
            return epcs, buf[i:]
        data = buf[i + 5:i + 5 + length]
        if length >= 6 and data[0] == 0x00:
            epc_len = data[5]
            epc = data[6:6 + epc_len]
            if len(epc) == epc_len:
                epcs.append(epc.hex().upper())
        i = end


# Open the reader's serial port the first time it is needed, then keep it open
def _open_port():
    global _port
    if serial is None:
        raise ReaderError("pyserial is not installed. Run: pip install pyserial")
    if _port is None or not _port.is_open:
        try:
            _port = serial.Serial(RFID_PORT, RFID_BAUD, timeout=0.5)
        except serial.SerialException as err:
            _port = None
            raise ReaderError(f"Can't open the RFID reader on {RFID_PORT}. Is it plugged in? ({err})")
    return _port


# Ask the reader once and give back the EPCs of the tags it saw (each tag once, even if it was read many times)
def scan_once():
    global _port, _leftover
    with _lock:
        port = _open_port()
        try:
            port.write(READ_TAGS)
            time.sleep(REPLY_WAIT)
            data = _leftover + port.read(port.in_waiting)
        except (serial.SerialException, OSError) as err:
            # Close it so the next scan tries a fresh connection (the reader may have been unplugged)
            try:
                port.close()
            except Exception:
                pass
            _port = None
            raise ReaderError(f"Lost the RFID reader on {RFID_PORT}. ({err})")
        epcs, _leftover = parse_epcs(data)
        return list(dict.fromkeys(epcs))
