# devices/dc_motor_pwm.py
from periphery import PWM, GPIO


class DCMotorPWM:
    """
    PWM hardware usado como CLOCK (STEP) para CL57T
    - Duty fijo 50%
    - PWM solo activo cuando percent > 0
    """

    def __init__(self, cfg: dict):
        pwm_cfg = cfg.get("hard_pwm", {})
        step_cfg = cfg.get("stepper", {})

        chip = int(pwm_cfg.get("chip", 0))
        channel = int(pwm_cfg.get("channel", 0))

        self.F_MIN = float(step_cfg.get("f_min_hz", 200.0))
        self.F_MAX = float(step_cfg.get("f_max_hz", 2500.0))

        self._pwm = PWM(chip, channel)
        self._pwm_enabled = False

        # DIR
        self._dir = GPIO(
            step_cfg["dir_gpio_chip"],
            int(step_cfg["dir_gpio_line"]),
            "out",
        )
        self._dir.write(bool(step_cfg.get("dir_cw", True)))

        # ENABLE
        self._enable = GPIO(
            step_cfg["enable_gpio_chip"],
            int(step_cfg["enable_gpio_line"]),
            "out",
        )
        self._enable.write(False)  # Enable+

    def _start_pwm(self, freq: float):
        """
        Arranque seguro del PWM
        """
        self._pwm.frequency = freq
        self._pwm.duty_cycle = 0.5
        self._pwm.enable()
        self._pwm_enabled = True

    def _stop_pwm(self):
        if self._pwm_enabled:
            self._pwm.disable()
            self._pwm_enabled = False

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))

        if p <= 0.0:
            self._stop_pwm()
            return

        freq = self.F_MIN + (p / 100.0) * (self.F_MAX - self.F_MIN)

        if not self._pwm_enabled:
            # ✅ Arranque completo
            self._start_pwm(freq)
        else:
            # ✅ Cambio dinámico de frecuencia
            self._pwm.frequency = freq

    def close(self):
        try:
            self._stop_pwm()
            self._pwm.close()
        except Exception:
            pass
        try:
            self._enable.write(True)  # disable motor
            self._enable.close()
            self._dir.close()
        except Exception:
            pass