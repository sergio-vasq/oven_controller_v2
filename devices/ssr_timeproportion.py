import threading, time
try:
    from periphery import GPIO
except Exception:
    GPIO = None

class SSRTimeProportion:
    def __init__(self, gpio_chip: str, gpio_line: int, active_high: bool = True, window_s: float = 1.0):
        if GPIO is None:
            raise RuntimeError("python-periphery GPIO not available")
        self.gpio = GPIO(gpio_chip, gpio_line, "out")
        self.active_high = bool(active_high)
        self.window_s = float(window_s)
        self._duty = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
    def set_duty(self, duty_percent: float):
        self._duty = max(0.0, min(100.0, float(duty_percent)))
    def _set_output(self, on: bool):
        level = bool(on) if self.active_high else not bool(on)
        try:
            self.gpio.write(level)
        except Exception:
            pass
    def _loop(self):
        while not self._stop.is_set():
            on_time = self.window_s * (self._duty / 100.0)
            off_time = max(0.0, self.window_s - on_time)
            if on_time > 0:
                self._set_output(True)
                self._stop.wait(on_time)
            if off_time > 0 and not self._stop.is_set():
                self._set_output(False)
                self._stop.wait(off_time)
        self._set_output(False)
    def close(self):
        self._stop.set()
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.gpio.write(False if self.active_high else True)
        except Exception:
            pass
        try:
            self.gpio.close()
        except Exception:
            pass
