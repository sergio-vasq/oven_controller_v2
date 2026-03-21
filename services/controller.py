# services/controller.py
import threading, time
from typing import Optional, Callable, Tuple
from services.pid_algo import PID
from services.autotune import RelayAutoTuner

class ControllerV2:
    def __init__(
        self,
        thermocouple,
        heater,
        motor,
        storage,
        kp: float,
        ki: float,
        kd: float,
        sample_s: float,
        output_limits: Tuple[float, float],
        safety_cfg: dict,
        autotune_cfg: dict = None,
        on_update: Optional[Callable[[dict], None]] = None,
        fan=None,
    ):
        self.tc = thermocouple
        self.heater = heater
        self.motor = motor
        self.fan = fan
        self.storage = storage
        self.on_update = on_update

        self.pid = PID(
            kp, ki, kd,
            setpoint=25.0,
            sample_time=sample_s,
            output_limits=output_limits
        )
        self.enabled = False
        self.sample_s = sample_s

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

        self.safety = {
            "absolute_max_c": float(safety_cfg.get("absolute_max_c", 350.0)),
            "sensor_fault_action": safety_cfg.get("sensor_fault_action", "cut"),
            "max_over_sp_c": float(safety_cfg.get("max_over_sp_c", 40.0)),
        }

        self._status = {
            "pv": None,
            "sp": self.pid.setpoint,
            "u": 0.0,
            "enabled": self.enabled,
            "motor": 0.0,
            "alarm": None,
            "autotune": {"active": False},
            "fan": bool(self._read_fan_state()),
            "part_code": None,            # <-- NUEVO: parte activa
        }

        self.autotune = None
        self.autotune_cfg = autotune_cfg or {}
        if bool(self.autotune_cfg.get("enabled", False)):
            self._init_autotune()

    # ------------- FAN -------------
    def _read_fan_state(self) -> bool:
        try:
            if self.fan is None:
                return False
            return bool(self.fan.is_on())
        except Exception:
            return False

    def set_fan(self, on: bool):
        self._status["fan"] = bool(on)
        if self.fan is not None:
            try:
                self.fan.set_on(self._status["fan"])
            except Exception:
                pass

    def toggle_fan(self):
        self.set_fan(not self._status.get("fan", False))

    # --------- AUTOTUNE -----------
    def _init_autotune(self, params=None):
        cfg = dict(self.autotune_cfg)
        if params:
            cfg.update(params)
        self.autotune = RelayAutoTuner(
            setpoint_c=self.pid.setpoint,
            sample_s=self.sample_s,
            high_percent=float(cfg.get("relay_high_percent", 60.0)),
            low_percent=float(cfg.get("relay_low_percent", 0.0)),
            hysteresis_c=float(cfg.get("hysteresis_c", 2.0)),
            settle_cycles=int(cfg.get("settle_cycles", 1)),
            cycles_target=int(cfg.get("cycles_target", 6)),
            output_limits=(self.pid.min_out, self.pid.max_out),
            rule=str(cfg.get("rule", "zn_classic")),
        )
        self._status["autotune"] = {"active": True}
        self.enabled = False
        self._status["enabled"] = False

    def autotune_start(self, params: dict):
        if self.tc is None or self.heater is None:
            return False, "Thermocouple/SSR not available."
        self._init_autotune(params or {})
        # Mantenemos tus prints
        print("[AT] Autotune started with params:", params)
        return True, "Auto-tune started"

    def autotune_stop(self):
        self.autotune = None
        self._status["autotune"] = {"active": False}
        if self.heater is not None:
            try:
                self.heater.set_duty(0.0)
            except Exception:
                pass

    def autotune_apply(self):
        auto = self._status.get("autotune", {})
        if not auto.get("done"):
            return False, None
        kp, ki, kd = auto.get("Kp"), auto.get("Ki"), auto.get("Kd")
        if kp is None:
            return False, None
        self.set_gains(kp, ki, kd)
        return True, {"Kp": kp, "Ki": ki, "Kd": kd}

    # ----------- CONTROL ----------
    def start(self):
        self._stop.clear()
        if not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self, join_timeout: float = 2.0):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=join_timeout)

    def set_setpoint(self, temp_c: float):
        self.pid.setpoint = float(temp_c)
        self._status["sp"] = self.pid.setpoint
        self.pid.reset()
        if self.autotune:
            self._init_autotune()

    def set_gains(self, kp: float, ki: float, kd: float):
        self.pid.kp, self.pid.ki, self.pid.kd = float(kp), float(ki), float(kd)
        self.pid.reset()

    def enable_control(self, enable: bool):
        self.enabled = bool(enable)
        self._status["enabled"] = self.enabled
        if not enable and self.heater is not None:
            try:
                self.heater.set_duty(0.0)
                self._status["u"] = 0.0
            except Exception:
                pass

    def set_motor_speed(self, percent: float):
        self._status["motor"] = max(0.0, min(100.0, float(percent)))
        if self.motor is not None:
            try:
                self.motor.set_percent(self._status["motor"])
            except Exception:
                pass

    def apply_part(self, code: str):
        part = self.storage.get_part(code)
        if not part:
            return False, None
        self.set_setpoint(float(part["temp_setpoint"]))
        self.set_motor_speed(float(part["conveyor_speed"]))
        self._status["part_code"] = code     # <-- NUEVO: marca la parte activa
        return True, part

    # ------- EMERGENCY STOP -------
    def emergency_stop(self, sp_zero: bool = True, fan_on_after_stop: bool = False):
        self.enable_control(False)
        try:
            if self.heater is not None:
                self.heater.set_duty(0.0)
        except Exception:
            pass
        self.set_motor_speed(0.0)
        self.set_fan(bool(fan_on_after_stop))
        if sp_zero:
            self.set_setpoint(0.0)
        self.pid.reset()
        self._status["alarm"] = "EMERGENCY_STOP"

    # ------------- LOOP -----------
    def _loop(self):
        while not self._stop.is_set():
            now = time.monotonic()
            pv = None
            alarm = None

            try:
                if self.tc is not None:
                    pv = self.tc.read_c()
            except Exception:
                pv = None

            self._status["pv"] = pv
            cut = False

            if pv is None:
                if self.safety.get("sensor_fault_action") == "cut":
                    cut = True
                    alarm = "SENSOR_FAULT"
            else:
                if pv >= self.safety.get("absolute_max_c", 350.0):
                    cut = True
                    alarm = "ABS_MAX"
                elif pv - self.pid.setpoint > self.safety.get("max_over_sp_c", 40.0):
                    cut = True
                    alarm = "OVER_SP"

            u = self._status.get("u", 0.0)
            auto_status = self._status.get("autotune", {"active": False})

            if self.autotune and not cut and pv is not None:
                prog = self.autotune.update(pv, now)
                u = self.autotune.output()
                if self.heater is not None:
                    try:
                        self.heater.set_duty(u)
                    except Exception:
                        pass
                auto_status.update(prog)
                if prog.get("status") == "done":
                    auto_status["active"] = False
                    auto_status["done"] = True
                    self.autotune = None
            else:
                auto_status = {"active": False} if not self.autotune else auto_status

            if self.enabled and not cut and pv is not None:
                out = self.pid.compute(pv, now)
                if out is not None:
                    u = out
                    if self.heater is not None:
                        try:
                            self.heater.set_duty(u)
                        except Exception:
                            pass
            else:
                if (self.autotune is None) and (self.heater is not None):
                    try:
                        self.heater.set_duty(0.0)
                    except Exception:
                        pass
                self.pid.reset()
                u = 0.0

            self._status["u"] = u
            self._status["alarm"] = alarm or self._status.get("alarm")
            self._status["autotune"] = auto_status
            self._status["fan"] = self._read_fan_state()

            if self.on_update:
                try:
                    self.on_update(dict(self._status))
                except Exception:
                    pass

            self._stop.wait(self.pid.sample_time)
