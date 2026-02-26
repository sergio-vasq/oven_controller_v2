# devices/gpio_button.py
import threading, time
try:
    from periphery import GPIO
except Exception:
    GPIO = None

class GPIOButton:
    def __init__(self, gpio_chip: str, gpio_line: int, pull: str = "up", debounce_ms: int = 60, on_press=None):
        """
        pull: "up" | "down" | "none"  (si tu línea soporta bias por sysfs/chip, si no, usar RC externo)
        """
        if GPIO is None:
            raise RuntimeError("python-periphery GPIO not available")
        # Nota: python-periphery no maneja bias directamente en todas las plataformas.
        # Si tu chipexport soporta bias, podrías usar flags. Aquí asumimos wiring externo o default.
        self._gpio = GPIO(gpio_chip, int(gpio_line), "in")
        self._debounce = max(0, int(debounce_ms)) / 1000.0
        self._on_press = on_press
        self._stop = threading.Event()
        self._last = self._read()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _read(self) -> bool:
        try:
            return bool(self._gpio.read())
        except Exception:
            return self._last

    def _loop(self):
        # Simple edge-detect con debounce
        while not self._stop.is_set():
            cur = self._read()
            if cur != self._last:
                t0 = time.monotonic()
                time.sleep(self._debounce)
                cur2 = self._read()
                if cur2 == cur:  # estado estable
                    # Detecta flanco de "presionado". Ajusta si tu botón es activo-bajo.
                    pressed = (cur is True)  # si usas pull-up externo y botón a GND
                    if pressed and self._on_press:
                        try:
                            self._on_press()
                        except Exception:
                            pass
                    self._last = cur2
            time.sleep(0.005)

    def close(self):
        self._stop.set()
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self._gpio.close()
        except Exception:
            pass