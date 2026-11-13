import os
import subprocess
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


# Terminal colors so the RFID messages stand out from Flask's output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"


# The Pi doesn't know the CF600's USB id, so after a reboot /dev/ttyUSB0 is missing
# until we tell the usbserial driver about it. Only runs if the port isn't there yet.
def setup_reader():
    if os.path.exists(RFID_PORT):
        return
    print(f"{YELLOW}{RFID_PORT} not found, loading the usbserial driver for the RFID reader...{RESET}")
    subprocess.run(["sudo", "modprobe", "usbserial", "vendor=0x0483", "product=0x5750"])
    # Give Linux a moment to create the port
    time.sleep(1)
    if os.path.exists(RFID_PORT):
        print(f"{GREEN}RFID reader ready on {RFID_PORT}{RESET}")
    else:
        print(f"{RED}RFID reader still not found on {RFID_PORT}. Is it plugged in?{RESET}")


# The reader is unplugged or not answering
class ReaderError(Exception):
    pass


# Frame: CF | addr | cmd(2) | len | status | rssi(2) | ant | ? | epc_len | epc | crc(2)
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


# Opened the first time it is needed, then kept open
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


# The EPCs the reader sees right now, each one once
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
