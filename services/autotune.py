import math, time
from statistics import mean


class RelayAutoTuner:
    def __init__(self, setpoint_c: float, sample_s: float, high_percent: float = 60.0, low_percent: float = 0.0, hysteresis_c: float = 2.0, settle_cycles:int=1, cycles_target:int=6, output_limits=(0.0, 100.0), rule: str = "zn_classic"):
        self.sp = float(setpoint_c)
        self.sample_s = float(sample_s)
        self.high = max(output_limits[0], min(output_limits[1], float(high_percent)))
        self.low = max(output_limits[0], min(output_limits[1], float(low_percent)))
        self.hyst = max(0.1, float(hysteresis_c))
        self.settle_cycles = max(0, int(settle_cycles))
        self.cycles_target = max(3, int(cycles_target))
        self.out_min, self.out_max = output_limits
        self.rule = rule
        self._state = "init"
        self._last_cross_time = None
        self._on = False
        self._periods = []
        self._peaks_high = []
        self._peaks_low = []
        self._curr_peak_high = None
        self._curr_peak_low = None
        self._cross_dir = None
        self._cycles_count = 0

    def output(self):
        return self.high if self._on else self.low

    def update(self, pv: float, now: float):
        if pv is None:
            return {"status": "fault"}
        if self._state == "init":
            self._on = pv < self.sp
            self._state = "run"
            self._last_cross_time = now
            return {"status": "running"}
        if self._on:
            self._curr_peak_high = (
                pv
                if self._curr_peak_high is None or pv > self._curr_peak_high
                else self._curr_peak_high
            )
        else:
            self._curr_peak_low = (
                pv
                if self._curr_peak_low is None or pv < self._curr_peak_low
                else self._curr_peak_low
            )
        if self._on and pv >= self.sp + self.hyst:
            self._on = False
            self._cross("up", now)
        elif (not self._on) and pv <= self.sp - self.hyst:
            self._on = True
            self._cross("down", now)
        prog = {"status": "running", "cycles": self._cycles_count}
        if self._is_done():
            Ku, Tu = self._estimate_ku_tu()
            Kp, Ki, Kd = self._suggest_pid(Ku, Tu)
            prog.update(
                {"status": "done", "Ku": Ku, "Tu": Tu, "Kp": Kp, "Ki": Ki, "Kd": Kd}
            )
        return prog

    def _cross(self, direction: str, now: float):
        print(
            f"[AT-X] dir={direction}, now={now:.2f}, last={self._last_cross_time if self._last_cross_time else None}, prev={self._cross_dir}, pending={getattr(self,'_pending_half', None)}"
        )
        if self._cross_dir is None:
            self._cross_dir = direction
            self._last_cross_time = now
            self._close_peak(direction)
            return
        if direction != self._cross_dir:
            half = now - self._last_cross_time
            if not hasattr(self, "_pending_half"):
                self._pending_half = half
            else:
                self._periods.append(self._pending_half + half)
                del self._pending_half
                self._cycles_count += 1
            self._cross_dir = direction
            self._last_cross_time = now
            self._close_peak(direction)

    def _close_peak(self, direction: str):
        if direction == "up" and self._curr_peak_high is not None:
            self._peaks_high.append(self._curr_peak_high)
            self._curr_peak_high = None
        elif direction == "down" and self._curr_peak_low is not None:
            self._peaks_low.append(self._curr_peak_low)
            self._curr_peak_low = None

    def _is_done(self):
        usable = max(0, self._cycles_count - self.settle_cycles)
        return usable >= self.cycles_target and len(self._periods) >= self.cycles_target

    def _estimate_ku_tu(self):
        recent = self._periods[-self.cycles_target :]
        Tu = mean(recent) if recent else None
        ph = self._peaks_high[-self.cycles_target :]
        pl = self._peaks_low[-self.cycles_target :]
        print("[AT-AMP]", f"peaks_high={ph}", f"peaks_low={pl}")

        if self._peaks_high and self._peaks_low:
            a = (mean(ph) - mean(pl)) / 2.0
        else:
            a = None

        d = (self.high - self.low) / 2.0
        Ku = (4.0 * d / (math.pi * a)) if (a and a > 0) else None

        # DEBUG extra:
        print("[AT-AMP2]", f"a={a}", f"d={d}", f"Ku={Ku}", f"Tu={Tu}")
        return Ku, Tu

    def _suggest_pid(self, Ku, Tu):
        if not Ku or not Tu:
            return None, None, None
        r = (self.rule or "zn_classic").lower()
        if r == "zn_no_overshoot":
            Kp = 0.33 * Ku
            Ti = Tu
            Td = Tu / 3.0
        elif r == "tyreus_luyben":
            Kp = 0.454 * Ku
            Ti = Tu / 2.2
            Td = Tu / 6.3
        else:
            Kp = 0.6 * Ku
            Ti = Tu / 2.0
            Td = Tu / 8.0
        Ki = Kp / Ti if Ti else 0.0
        Kd = Kp * Td if Td else 0.0
        return Kp, Ki, Kd
