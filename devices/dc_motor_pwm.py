import threading
try:
    from periphery import PWM, GPIO
except Exception:
    PWM = None
    GPIO = None


class DCMotorPWM:
    """
    Reutilizado como generador de clock STEP para driver CL57T.
    - PWM hardware
    - Duty fijo 50 %
    - Frecuencia variable según porcentaje
    """

    def __init__(self, cfg: dict):
        if PWM is None:
            raise RuntimeError("python-periphery PWM not available")

        step_cfg = cfg.get("stepper", {}) or {}
        pwm_cfg = cfg.get("hard_pwm", {}) or {}

        # ---- PWM = STEP ----
        chip = int(pwm_cfg.get("chip", 0))
        channel = int(pwm_cfg.get("channel", 0))
        self._pwm = PWM(chip, channel)

        # Duty SIEMPRE 50 %
        self._pwm.duty_cycle = 0.5

        # Periodos configurables (µs)
        self.T_MIN_US = float(step_cfg.get("tmin_us", 200.0))    # 100 %
        self.T_MAX_US = float(step_cfg.get("tmax_us", 1000.0))   # 1 %

        self._enabled = True
        self._pwm.enable()

        # ---- DIR ----
        self._dir = None
        if GPIO and "dir_gpio_line" in step_cfg:
            self._dir = GPIO(
                step_cfg.get("dir_gpio_chip", "/dev/gpiochip4"),
                int(step_cfg.get("dir_gpio_line")),
                "out",
            )
            self._dir.write(bool(step_cfg.get("dir_cw", True)))

        # ---- ENABLE ----
        self._enable = None
        if GPIO and "enable_gpio_line" in step_cfg:
            self._enable = GPIO(
                step_cfg.get("enable_gpio_chip", "/dev/gpiochip4"),
                int(step_cfg.get("enable_gpio_line")),
                "out",
            )
            # Enable+ a 0
            self._enable.write(False)

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))

        if p <= 0:
            # Sin pulsos = motor detenido
            self._pwm.frequency = 1.0
            self._pwm.duty_cycle = 0.0
            return

        # Duty fijo 50 %
        self._pwm.duty_cycle = 0.5

        # Map % → semi‑periodo
        p = max(1.0, p)
        semi_us = self.T_MAX_US - ((p - 1.0) / 99.0) * (self.T_MAX_US - self.T_MIN_US)

        # Periodo completo = 2 * semi
        freq = 1_000_000.0 / (2.0 * semi_us)

        self._pwm.frequency = freq

    def close(self):
        try:
            self._pwm.duty_cycle = 0.0
            self._pwm.disable()
            self._pwm.close()
        except Exception:
            pass
        try:
            if self._dir:
                self._dir.close()
            if self._enable:
                self._enable.write(True)  # disable
                self._enable.close()
        except Exception:
            pass
