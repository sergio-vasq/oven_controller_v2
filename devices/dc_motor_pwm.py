# devices/dc_motor_pwm.py
from periphery import PWM, GPIO


class DCMotorPWM:
    """
    Usado como generador de CLOCK (STEP) para driver CL57T
    - PWM hardware
    - Duty fijo 50 %
    - Frecuencia variable según porcentaje
    """

    def __init__(self, cfg: dict):
        motor_cfg = cfg.get("motor", {})
        pwm_cfg = cfg.get("hard_pwm", {})
        step_cfg = cfg.get("stepper", {})

        # ---- PWM = STEP ----
        chip = int(pwm_cfg.get("chip", 0))
        channel = int(pwm_cfg.get("channel", 0))

        self._pwm = PWM(chip, channel)
        self._pwm.duty_cycle = 0.5
        self._pwm.frequency = 200.0
        self._pwm.enable()

        # ---- Frecuencia ----
        self.F_MIN = float(step_cfg.get("f_min_hz", 200.0))
        self.F_MAX = float(step_cfg.get("f_max_hz", 2500.0))

        # ---- DIR ----
        self._dir = GPIO(
            step_cfg["dir_gpio_chip"],
            int(step_cfg["dir_gpio_line"]),
            "out",
        )
        self._dir.write(bool(step_cfg.get("dir_cw", True)))

        # ---- ENABLE ----
        self._enable = GPIO(
            step_cfg["enable_gpio_chip"],
            int(step_cfg["enable_gpio_line"]),
            "out",
        )
        self._enable.write(False)  # Enable+

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))

        if p <= 0.0:
            # Motor detenido
            self._pwm.duty_cycle = 0.0
            return

        self._pwm.duty_cycle = 0.5

        freq = self.F_MIN + (p / 100.0) * (self.F_MAX - self.F_MIN)
        self._pwm.frequency = freq

    def close(self):
        try:
            self._pwm.duty_cycle = 0.0
            self._pwm.disable()
            self._pwm.close()
        except Exception:
            pass
        try:
            self._dir.close()
            self._enable.write(True)
            self._enable.close()
        except Exception:
            pass