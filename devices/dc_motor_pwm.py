import threading, time
try:
    from periphery import GPIO, PWM
except Exception:
    GPIO = None
    PWM = None

class DCMotorPWM:
    def __init__(self, cfg: dict):
        self.mode = cfg.get("mode", "software").lower()
        self.percent = 0.0
        self._stop = threading.Event()
        self.thread = None
        self._gpio = None
        self._active_high = True
        self._period = 0.01
        self._pwm = None
        if self.mode == "hardware":
            if PWM is None:
                raise RuntimeError("python-periphery PWM not available")
            chip = int(cfg.get("hard_pwm", {}).get("chip", 0))
            ch = int(cfg.get("hard_pwm", {}).get("channel", 0))
            freq = float(cfg.get("hard_pwm", {}).get("frequency_hz", 1000.0))
            self._pwm = PWM(chip, ch)
            self._pwm.frequency = freq
            self._pwm.duty_cycle = 0.0
            self._pwm.enable()
        else:
            if GPIO is None:
                raise RuntimeError("python-periphery GPIO not available")
            sp = cfg.get("soft_pwm", {})
            chip = sp.get("gpio_chip", "/dev/gpiochip0")
            line = int(sp.get("gpio_line", 24))
            self._active_high = bool(sp.get("active_high", True))
            pwm_hz = float(sp.get("pwm_hz", 250.0))
            self._period = 1.0 / max(1.0, pwm_hz)
            self._gpio = GPIO(chip, line, "out")
            self.thread = threading.Thread(target=self._soft_loop, daemon=True)
            self.thread.start()
    def set_percent(self, percent: float):
        self.percent = max(0.0, min(100.0, float(percent)))
        if self.mode == "hardware" and self._pwm is not None:
            try:
                self._pwm.duty_cycle = self.percent / 100.0
            except Exception:
                pass
    def _write_gpio(self, on: bool):
        lvl = bool(on) if self._active_high else not bool(on)
        try:
            self._gpio.write(lvl)
        except Exception:
            pass
    def _soft_loop(self):
        while not self._stop.is_set():
            duty = self.percent / 100.0
            on_time = self._period * duty
            off_time = self._period - on_time
            if on_time > 0:
                self._write_gpio(True)
                self._stop.wait(on_time)
            if off_time > 0 and not self._stop.is_set():
                self._write_gpio(False)
                self._stop.wait(off_time)
        self._write_gpio(False)
    def close(self):
        self._stop.set()
        if self.thread:
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass
        try:
            if self._pwm is not None:
                self._pwm.disable()
                self._pwm.close()
        except Exception:
            pass
        try:
            if self._gpio is not None:
                self._write_gpio(False)
                self._gpio.close()
        except Exception:
            pass
