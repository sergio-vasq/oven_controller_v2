# devices/dc_motor_pwm.py
from periphery import PWM, GPIO
import time


class DCMotorPWM:
    """
    PWM hardware usado como CLOCK (STEP) para CL57T
    - Duty fijo 50%
    - PWM solo activo cuando percent > 0
    - Rearme del driver en saltos grandes de velocidad
    """

    def __init__(self, cfg: dict):
        pwm_cfg = cfg.get("hard_pwm", {})
        step_cfg = cfg.get("stepper", {})

        chip = int(pwm_cfg.get("chip", 0))
        channel = int(pwm_cfg.get("channel", 0))

        self.F_MIN = float(step_cfg.get("f_min_hz", 200.0))
        self.F_MAX = float(step_cfg.get("f_max_hz", 1500.0))

        self._pwm = PWM(chip, channel)
        self._pwm_enabled = False

        self._current_freq = None          # ← NUEVO
        self._reset_threshold = 400.0      # ← NUEVO (Hz)
        self._reset_delay = 0.3            # ← NUEVO (seg)

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
        self._pwm.frequency = freq
        self._pwm.duty_cycle = 0.5
        self._pwm.enable()
        self._pwm_enabled = True
        self._current_freq = freq           # ← NUEVO

    def _stop_pwm(self):
        if self._pwm_enabled:
            self._pwm.disable()
            self._pwm_enabled = False
        self._current_freq = None           # ← NUEVO

    def _reset_driver(self):
        """
        Rearme controlado del CL57T
        """
        try:
            self._enable.write(True)         # disable CL57T
            time.sleep(self._reset_delay)
            self._enable.write(False)        # enable CL57T
            time.sleep(0.5)
        except Exception:
            pass

    def set_percent(self, percent: float):
        p = max(0.0, min(100.0, float(percent)))

        if p <= 0.0:
            self._stop_pwm()
            return

        freq = self.F_MIN + (p / 100.0) * (self.F_MAX - self.F_MIN)

        # Clamp duro (seguridad extra)
        if freq < self.F_MIN:
            freq = self.F_MIN
        elif freq > self.F_MAX:
            freq = self.F_MAX

        # ← NUEVO: detección de salto grande
        force_from_min = False
        if self._current_freq is not None:
            delta = abs(freq - self._current_freq)
            if delta >= self._reset_threshold:
                self._reset_driver()
                force_from_min = True

        if not self._pwm_enabled:
            if force_from_min:
                self._start_pwm(self.F_MIN)
                self._current_freq = self.F_MIN
            else:
                self._start_pwm(freq)
        else:
            try:
                self._pwm.duty_cycle = 0.0
                self._pwm.frequency = freq
                self._pwm.duty_cycle = 0.5
                self._current_freq = freq
            except OSError as e:
                print(f"[PWM WARN] Frequency rejected: {freq} Hz → {e}")

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
