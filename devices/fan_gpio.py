# devices/fan_gpio.py
import threading
try:
    from periphery import GPIO
except Exception:
    GPIO = None

class FanGPIO:
    def __init__(self, gpio_chip: str, gpio_line: int, active_high: bool = True, default_on: bool = False):
        if GPIO is None:
            raise RuntimeError("python-periphery GPIO not available")
        self._gpio = GPIO(gpio_chip, int(gpio_line), "out")
        self._active_high = bool(active_high)
        self._state = bool(default_on)
        self._write_hw(self._state)

    def _write_hw(self, on: bool):
        lvl = bool(on) if self._active_high else (not bool(on))
        try:
            self._gpio.write(lvl)
        except Exception:
            pass

    def set_on(self, on: bool):
        self._state = bool(on)
        self._write_hw(self._state)

    def is_on(self) -> bool:
        return self._state

    def toggle(self):
        self.set_on(not self._state)

    def close(self):
        try:
            # apaga al salir
            self._write_hw(False)
            self._gpio.close()
        except Exception:
            pass