import threading
import time
try:
    from periphery import GPIO
except Exception:
    GPIO = None


class StepMotorClock:
    """
    Generador de señal STEP/DIR para driver tipo CL57T.

    - percent (1..100) mapea a frecuencia (periodo variable)
    - Duty fijo 50%
    - Tmin y Tmax ajustables (hardcodeados, fácil de afinar)
    """

    def __init__(self, cfg: dict):
        if GPIO is None:
            raise RuntimeError("python-periphery GPIO not available")

        step_cfg = cfg.get("stepper", {}) or {}

        self._step = GPIO(
            step_cfg.get("step_gpio_chip", "/dev/gpiochip0"),
            int(step_cfg.get("step_gpio_line", 0)),
            "out",
        )

        self._dir = GPIO(
            step_cfg.get("dir_gpio_chip", "/dev/gpiochip0"),
            int(step_cfg.get("dir_gpio_line", 1)),
            "out",
        )

        self._enable = None
        if "enable_gpio_line" in step_cfg:
            self._enable = GPIO(
                step_cfg.get("enable_gpio_chip", "/dev/gpiochip0"),
                int(step_cfg.get("enable_gpio_line")),
                "out",
            )
            self._enable.write(False)  # Enable+ a 0

        # Dirección fija CW por ahora
        self._dir.write(True)

        # ---- Ajustables ----
        self.T_MIN_US = float(step_cfg.get("tmin_us", 200.0))   # 100 %
        self.T_MAX_US = float(step_cfg.get("tmax_us", 1000.0))  # 1 %

        self._half_period = None
        self._stop = threading.Event()
        self._percent = 0.0

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))
        self._percent = p

        if p <= 0:
            self._half_period = None
            try:
                self._step.write(False)
            except Exception:
                pass
            return

        # Lineal 1..100 → Tmax..Tmin
        p = max(1.0, p)
        span = self.T_MAX_US - self.T_MIN_US
        self._half_period = (
            self.T_MAX_US - ((p - 1.0) / 99.0) * span
        ) / 1_000_000.0  # a segundos

    def _loop(self):
        while not self._stop.is_set():
            hp = self._half_period
            if hp is None:
                self._stop.wait(0.01)
                continue
            try:
                self._step.write(True)
                self._stop.wait(hp)
                self._step.write(False)
                self._stop.wait(hp)
            except Exception:
                pass

        try:
            self._step.write(False)
        except Exception:
            pass

    def close(self):
        self._stop.set()
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self._step.close()
            self._dir.close()
        except Exception:
            pass
        try:
            if self._enable:
                self._enable.write(True)  # Disable motor
                self._enable.close()
        except Exception:
            pass