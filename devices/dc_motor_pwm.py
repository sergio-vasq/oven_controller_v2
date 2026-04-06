from periphery import PWM, GPIO

class DCMotorPWM:
    """
    PWM hardware usado como CLOCK (STEP) para CL57T
    - Duty fijo 50 %
    - PWM solo activo cuando percent > 0
    """

    def __init__(self, cfg: dict):
        pwm_cfg = cfg.get("hard_pwm", {})
        step_cfg = cfg.get("stepper", {})

        chip = int(pwm_cfg.get("chip", 0))
        channel = int(pwm_cfg.get("channel", 0))

        # PWM = STEP
        self._pwm = PWM(chip, channel)
        self._pwm.frequency = float(step_cfg.get("f_min_hz", 200.0))
        self._pwm.duty_cycle = 0.5
        self._pwm_enabled = False   # ← CLAVE

        # Frecuencia
        self.F_MIN = float(step_cfg.get("f_min_hz", 200.0))
        self.F_MAX = float(step_cfg.get("f_max_hz", 2500.0))

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

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))

        if p <= 0.0:
            # 🔴 DETENER MOTOR
            if self._pwm_enabled:
                self._pwm.disable()
                self._pwm_enabled = False
            return

        # ✅ Arranque controlado
        freq = self.F_MIN + (p / 100.0) * (self.F_MAX - self.F_MIN)
        self._pwm.frequency = freq

        if not self._pwm_enabled:
            self._pwm.enable()
            self._pwm_enabled = True

    def close(self):
        try:
            if self._pwm_enabled:
                self._pwm.disable()
            self._pwm.close()
        except Exception:
            pass
        try:
            self._enable.write(True)
            self._enable.close()
            self._dir.close()
        except Exception:
            pass
