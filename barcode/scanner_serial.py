from typing import Callable
import serial, threading

class SerialBarcodeScanner:
    def __init__(self, port: str, baudrate: int, timeout: float, on_code: Callable[[str], None]):
        if not timeout or timeout <= 0:
            timeout = 0.1
        self.on_code = on_code
        self.stop_flag = False
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        self.thread = threading.Thread(target=self._loop, daemon=True)
    def start(self):
        self.thread.start()
    def _loop(self):
        buf = bytearray()
        while not self.stop_flag:
            b = self.ser.read(1)
            if not b:
                continue
            if b in (b'', b'
'):
                if buf:
                    code = buf.decode("utf-8", errors="ignore").strip()
                    buf.clear()
                    if code:
                        try:
                            self.on_code(code)
                        except Exception:
                            pass
            else:
                buf.extend(b)
    def stop(self, join_timeout: float = 2.0):
        self.stop_flag = True
        try:
            self.thread.join(timeout=join_timeout)
        except Exception:
            pass
        try:
            self.ser.close()
        except Exception:
            pass
