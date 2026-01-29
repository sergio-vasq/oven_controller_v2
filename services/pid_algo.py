import time
class PID:
    def __init__(self, kp, ki, kd, setpoint=0.0, sample_time=0.5, output_limits=(0.0, 100.0)):
        self.kp = float(kp); self.ki = float(ki); self.kd = float(kd)
        self.setpoint = float(setpoint); self.sample_time = float(sample_time)
        self.min_out, self.max_out = output_limits
        self._last_time = None; self._last_err = 0.0; self._integral = 0.0
    def reset(self):
        self._last_time = None; self._last_err = 0.0; self._integral = 0.0
    def compute(self, pv, now=None):
        if now is None:
            now = time.monotonic()
        if self._last_time is None:
            self._last_time = now; self._last_err = self.setpoint - pv; return None
        dt = now - self._last_time
        if dt < self.sample_time: return None
        error = self.setpoint - pv
        self._integral += error * dt
        d_err = (error - self._last_err)/dt if dt>0 else 0.0
        u = self.kp*error + self.ki*self._integral + self.kd*d_err
        if u > self.max_out:
            u = self.max_out
            if error > 0: self._integral -= error*dt
        elif u < self.min_out:
            u = self.min_out
            if error < 0: self._integral -= error*dt
        self._last_time = now; self._last_err = error
        return u
