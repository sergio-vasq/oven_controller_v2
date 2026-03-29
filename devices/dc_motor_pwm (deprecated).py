import threading
import time

try:
    from periphery import GPIO, PWM
except Exception:
    GPIO = None
    PWM = None



class DCMotorPWM:
    """
    Control de motor DC con:
      - Modo hardware: 1 canal PWM (para RPWM en BTS7960) + GPIOs de enable (R_EN/L_EN) opcionales.
      - Modo software: PWM por bit-bang sobre un GPIO (comportamiento original).

    Notas para BTS7960 (un solo sentido):
      - Conecta RPWM a este PWM hardware.
      - LPWM a GND (no usado en software).
      - R_EN = HIGH, L_EN = HIGH (habilitan el puente). Se controlan aquí si defines 'enables' en el YAML.

    Config:
      motor:
        mode: "hardware" | "software"
        hard_pwm:
          chip: <int>
          channel: <int>
          frequency_hz: <float>
        invert_pwm: <bool>           # NUEVO: invierte el duty (0..1 -> 1..0) en modo hardware
        enables:
          r_en: { gpio_chip, gpio_line, active_high }
          l_en: { gpio_chip, gpio_line, active_high }
        soft_pwm:
          gpio_chip: "/dev/gpiochipX"
          gpio_line: <int>
          active_high: <bool>
          pwm_hz: <float>
    """

    def __init__(self, cfg: dict):
        self.mode = cfg.get("mode", "software").lower()
        self.percent = 0.0
        self._stop = threading.Event()
        self.thread = None

        # GPIO para soft-PWM (solo en modo software)
        self._gpio = None
        self._active_high = True
        self._period = 0.01

        # PWM hardware (RPWM)
        self._pwm = None

        # Inversión de duty en HW (por polaridad invertida del pin)
        self._invert_hw = bool(cfg.get("invert_pwm", False))

        # GPIOs de enable (opcionales)
        self._r_en_gpio = None
        self._l_en_gpio = None

        if self.mode == "hardware":
            if PWM is None:
                raise RuntimeError("python-periphery PWM not available")

            hp = cfg.get("hard_pwm", {}) or {}
            chip = int(hp.get("chip", 0))
            ch = int(hp.get("channel", 0))
            freq = float(hp.get("frequency_hz", 1000.0))

            # Abrir PWM (RPWM)
            self._pwm = PWM(chip, ch)
            self._pwm.frequency = freq
            # Duty inicial: respeta inversión
            initial_duty = (1.0 - 0.0) if self._invert_hw else 0.0
            self._pwm.duty_cycle = initial_duty
            self._pwm.enable()

            # Habilitar ENs si están definidos
            if GPIO is None and ("enables" in cfg):
                # Si no hay GPIO disponible pero el usuario definió enables, avisa:
                raise RuntimeError("python-periphery GPIO not available (enables requested)")
            if GPIO is not None and ("enables" in cfg):
                ens = cfg.get("enables", {}) or {}

                # R_EN
                if "r_en" in ens:
                    r = ens["r_en"] or {}
                    r_chip = r.get("gpio_chip", "/dev/gpiochip0")
                    r_line = int(r.get("gpio_line", 0))
                    r_active_high = bool(r.get("active_high", True))
                    self._r_en_gpio = GPIO(r_chip, r_line, "out")
                    # HIGH lógico para habilitar
                    self._r_en_gpio.write(True if r_active_high else False)

                # L_EN
                if "l_en" in ens:
                    l = ens["l_en"] or {}
                    l_chip = l.get("gpio_chip", "/dev/gpiochip0")
                    l_line = int(l.get("gpio_line", 0))
                    l_active_high = bool(l.get("active_high", True))
                    self._l_en_gpio = GPIO(l_chip, l_line, "out")
                    self._l_en_gpio.write(True if l_active_high else False)

        else:
            # Modo software (comportamiento original)
            if GPIO is None:
                raise RuntimeError("python-periphery GPIO not available")
            sp = cfg.get("soft_pwm", {}) or {}
            chip = sp.get("gpio_chip", "/dev/gpiochip0")
            line = int(sp.get("gpio_line", 24))
            self._active_high = bool(sp.get("active_high", True))
            pwm_hz = float(sp.get("pwm_hz", 250.0))
            self._period = 1.0 / max(1.0, pwm_hz)
            self._gpio = GPIO(chip, line, "out")
            self.thread = threading.Thread(target=self._soft_loop, daemon=True)
            self.thread.start()


    def set_percent(self, percent: float):
        """
        Ajusta el duty del PWM (0..100 %).
        - En hardware: duty en RPWM (con inversión opcional si invert_pwm=true).
        - En software: bit-bang sobre GPIO.
        """
        self.percent = max(0.0, min(100.0, float(percent)))

        if self.mode == "hardware" and self._pwm is not None:
            try:
                duty_01 = self.percent / 100.0
                if self._invert_hw:
                    duty_01 = 1.0 - duty_01
                self._pwm.duty_cycle = duty_01
            except Exception:
                # Evitar que un fallo rompa el hilo principal
                pass

    # --------- Internos para modo software ---------
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

        # Apaga al salir
        self._write_gpio(False)

    # --------- Cierre ordenado ---------
    def close(self):
        # Detener soft-PWM si aplica
        self._stop.set()
        if self.thread:
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass

        # Deshabilitar PWM hardware
        try:
            if self._pwm is not None:
                # Apaga asegurando duty = "apagado" según inversión
                off_duty = (1.0 - 0.0) if self._invert_hw else 0.0
                self._pwm.duty_cycle = off_duty
                self._pwm.disable()
                self._pwm.close()
        except Exception:
            pass

        # Deshabilitar ENs (LOW por seguridad)
        try:
            if self._r_en_gpio is not None:
                self._r_en_gpio.write(False)
                self._r_en_gpio.close()
        except Exception:
            pass
        try:
            if self._l_en_gpio is not None:
                self._l_en_gpio.write(False)
                self._l_en_gpio.close()
        except Exception:
            pass

        # Liberar GPIO soft-PWM
        try:
            if self._gpio is not None:
                self._write_gpio(False)
                self._gpio.close()
        except Exception:
            pass