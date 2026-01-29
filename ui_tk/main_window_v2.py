import tkinter as tk
from tkinter import ttk, messagebox

class MainWindow(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.master = master
        self.master.title("Oven Controller V2")
        self.master.geometry("1060x720")
        self.grid(sticky="nsew")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # external callbacks
        self.cb_on_scan = None
        self.cb_on_set_sp = None
        self.cb_on_set_pid = None
        self.cb_on_enable = None
        self.cb_on_motor = None
        self.cb_on_add = None
        self.cb_on_update = None
        self.cb_on_delete = None
        self.cb_on_autotune_start = None
        self.cb_on_autotune_stop = None
        self.cb_on_autotune_apply = None

        # STATUS
        status = ttk.LabelFrame(self, text="Status")
        status.grid(row=0, column=0, sticky="ew")
        for i in range(6):
            status.columnconfigure(i, weight=1)
        self.lbl_sp = ttk.Label(status, text="SP: — °C")
        self.lbl_pv = ttk.Label(status, text="PV: — °C")
        self.lbl_u  = ttk.Label(status, text="Heater: — %")
        self.lbl_motor = ttk.Label(status, text="Motor: — %")
        self.lbl_mode = ttk.Label(status, text="Mode: DISABLED")
        self.lbl_alarm = ttk.Label(status, text="Alarm: —")
        for i, w in enumerate((self.lbl_sp, self.lbl_pv, self.lbl_u, self.lbl_motor, self.lbl_mode, self.lbl_alarm)):
            w.grid(row=0, column=i, padx=8, pady=6, sticky="w")

        # CONTROL PANEL
        pnl = ttk.LabelFrame(self, text="Control")
        pnl.grid(row=1, column=0, sticky="ew", pady=(8,0))
        for i in range(10): pnl.columnconfigure(i, weight=1)
        ttk.Label(pnl, text="Setpoint (°C)").grid(row=0, column=0, sticky="w")
        self.ent_sp = ttk.Entry(pnl, width=10)
        self.ent_sp.grid(row=0, column=1, sticky="w")
        ttk.Button(pnl, text="Apply SP", command=self._apply_sp).grid(row=0, column=2, sticky="w", padx=6)

        ttk.Label(pnl, text="Kp").grid(row=0, column=3, sticky="e"); self.ent_kp = ttk.Entry(pnl, width=8); self.ent_kp.grid(row=0, column=4, sticky="w")
        ttk.Label(pnl, text="Ki").grid(row=0, column=5, sticky="e"); self.ent_ki = ttk.Entry(pnl, width=8); self.ent_ki.grid(row=0, column=6, sticky="w")
        ttk.Label(pnl, text="Kd").grid(row=0, column=7, sticky="e"); self.ent_kd = ttk.Entry(pnl, width=8); self.ent_kd.grid(row=0, column=8, sticky="w")
        ttk.Button(pnl, text="Apply PID", command=self._apply_pid).grid(row=0, column=9, sticky="w", padx=6)

        self.btn_enable = ttk.Button(pnl, text="Enable", command=self._toggle_enable)
        self.btn_enable.grid(row=0, column=10, padx=6)

        # MOTOR
        mot = ttk.LabelFrame(self, text="Motor speed (%)")
        mot.grid(row=2, column=0, sticky="ew", pady=(8,0))
        mot.columnconfigure(0, weight=1)
        self.scale_motor = ttk.Scale(mot, from_=0, to=100, orient="horizontal", command=self._on_motor_changed)
        self.scale_motor.set(0)
        self.scale_motor.grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        # AUTOTUNE
        at = ttk.LabelFrame(self, text="Auto-tune (Relay)")
        at.grid(row=3, column=0, sticky="ew", pady=(8,0))
        for i in range(12): at.columnconfigure(i, weight=1)
        ttk.Label(at, text="SP (°C)").grid(row=0, column=0, sticky="e"); self.at_sp = ttk.Entry(at, width=10); self.at_sp.grid(row=0, column=1, sticky="w")
        ttk.Label(at, text="High %").grid(row=0, column=2, sticky="e"); self.at_high = ttk.Entry(at, width=8); self.at_high.grid(row=0, column=3, sticky="w")
        ttk.Label(at, text="Low %").grid(row=0, column=4, sticky="e"); self.at_low = ttk.Entry(at, width=8); self.at_low.grid(row=0, column=5, sticky="w")
        ttk.Label(at, text="Hyst (°C)").grid(row=0, column=6, sticky="e"); self.at_hyst = ttk.Entry(at, width=8); self.at_hyst.grid(row=0, column=7, sticky="w")
        ttk.Label(at, text="Rule").grid(row=0, column=8, sticky="e"); self.at_rule = ttk.Combobox(at, values=("zn_classic","zn_no_overshoot","tyreus_luyben"), width=16, state="readonly"); self.at_rule.grid(row=0, column=9, sticky="w")
        self.btn_at_start = ttk.Button(at, text="Start Auto-tune", command=self._at_start)
        self.btn_at_start.grid(row=0, column=10, padx=6)
        self.btn_at_stop = ttk.Button(at, text="Stop", command=self._at_stop)
        self.btn_at_stop.grid(row=0, column=11, padx=6)

        # Results line
        res = ttk.Frame(at)
        res.grid(row=1, column=0, columnspan=12, sticky="ew", pady=(6,4))
        for i in range(10): res.columnconfigure(i, weight=1)
        self.lbl_cycles = ttk.Label(res, text="Cycles: 0")
        self.lbl_ku = ttk.Label(res, text="Ku: —")
        self.lbl_tu = ttk.Label(res, text="Tu: — s")
        self.lbl_kp = ttk.Label(res, text="Kp: —")
        self.lbl_ki = ttk.Label(res, text="Ki: —")
        self.lbl_kd = ttk.Label(res, text="Kd: —")
        for i, w in enumerate((self.lbl_cycles, self.lbl_ku, self.lbl_tu, self.lbl_kp, self.lbl_ki, self.lbl_kd)):
            w.grid(row=0, column=i, padx=8, sticky="w")
        self.btn_at_apply = ttk.Button(at, text="Apply tuned gains", command=self._at_apply)
        self.btn_at_apply.grid(row=2, column=0, padx=6, pady=(4,6), sticky="w")

        # SCAN & LIBRARY
        scan = ttk.LabelFrame(self, text="Scan / Enter Part Code")
        scan.grid(row=4, column=0, sticky="ew", pady=(8,0))
        scan.columnconfigure(0, weight=1)
        self.txt_scan = ttk.Entry(scan)
        self.txt_scan.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.txt_scan.bind("<Return>", lambda e: self._do_scan())

        lib = ttk.LabelFrame(self, text="Part Library")
        lib.grid(row=5, column=0, sticky="nsew", pady=(8,0))
        lib.rowconfigure(0, weight=1); lib.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(lib, columns=("code","temp","speed","notes"), show="headings")
        for c, txt, w in (("code","Code",180),("temp","Temp (°C)",120),("speed","Speed",120),("notes","Notes",300)):
            self.table.heading(c, text=txt); self.table.column(c, width=w, anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew")

        frm = ttk.Frame(self); frm.grid(row=6, column=0, sticky="ew", pady=8)
        ttk.Label(frm, text="Code").grid(row=0, column=0, padx=(0,4), sticky="w"); self.txt_code = ttk.Entry(frm, width=24); self.txt_code.grid(row=0, column=1, padx=(0,12))
        ttk.Label(frm, text="Temp °C").grid(row=0, column=2, padx=(0,4), sticky="w"); self.txt_temp = ttk.Entry(frm, width=12); self.txt_temp.grid(row=0, column=3, padx=(0,12))
        ttk.Label(frm, text="Speed").grid(row=0, column=4, padx=(0,4), sticky="w"); self.txt_speed = ttk.Entry(frm, width=12); self.txt_speed.grid(row=0, column=5, padx=(0,12))
        ttk.Label(frm, text="Notes").grid(row=0, column=6, padx=(0,4), sticky="w"); self.txt_notes = ttk.Entry(frm, width=30); self.txt_notes.grid(row=0, column=7, padx=(0,12))
        ttk.Button(frm, text="Add", command=self._on_add).grid(row=0, column=8, padx=6)
        ttk.Button(frm, text="Update", command=self._on_update).grid(row=0, column=9, padx=6)
        ttk.Button(frm, text="Delete", command=self._on_delete).grid(row=0, column=10, padx=6)

        self.rowconfigure(5, weight=1)

        self.at_rule.set("zn_classic")

    def bind_callbacks(self, on_scan, on_set_sp, on_set_pid, on_enable, on_motor, on_add, on_update, on_delete, on_autotune_start, on_autotune_stop, on_autotune_apply):
        self.cb_on_scan = on_scan
        self.cb_on_set_sp = on_set_sp
        self.cb_on_set_pid = on_set_pid
        self.cb_on_enable = on_enable
        self.cb_on_motor = on_motor
        self.cb_on_add = on_add
        self.cb_on_update = on_update
        self.cb_on_delete = on_delete
        self.cb_on_autotune_start = on_autotune_start
        self.cb_on_autotune_stop = on_autotune_stop
        self.cb_on_autotune_apply = on_autotune_apply

    def update_status(self, data: dict):
        sp = data.get("sp")
        pv = data.get("pv")
        u  = data.get("u")
        mot = data.get("motor")
        ena = data.get("enabled")
        alarm = data.get("alarm")
        self.lbl_sp.config(text=f"SP: {sp:.1f} °C" if sp is not None else "SP: — °C")
        self.lbl_pv.config(text=f"PV: {pv:.1f} °C" if pv is not None else "PV: — °C")
        self.lbl_u.config(text=f"Heater: {u:.1f} %")
        self.lbl_motor.config(text=f"Motor: {mot:.1f} %")
        self.lbl_mode.config(text=f"Mode: {'ENABLED' if ena else 'DISABLED'}")
        self.lbl_alarm.config(text=f"Alarm: {alarm if alarm else '—'}")
        at = data.get("autotune", {}) or {}
        if at.get("active"):
            self.lbl_cycles.config(text=f"Cycles: {at.get('cycles',0)}")
        if at.get("status") == "done":
            Ku, Tu = at.get("Ku"), at.get("Tu")
            Kp, Ki, Kd = at.get("Kp"), at.get("Ki"), at.get("Kd")
            self.lbl_ku.config(text=f"Ku: {Ku:.3f}" if Ku else "Ku: —")
            self.lbl_tu.config(text=f"Tu: {Tu:.2f} s" if Tu else "Tu: — s")
            self.lbl_kp.config(text=f"Kp: {Kp:.3f}" if Kp else "Kp: —")
            self.lbl_ki.config(text=f"Ki: {Ki:.3f}" if Ki else "Ki: —")
            self.lbl_kd.config(text=f"Kd: {Kd:.3f}" if Kd else "Kd: —")

    def load_parts(self, parts):
        for iid in self.table.get_children():
            self.table.delete(iid)
        for p in parts:
            self.table.insert('', 'end', values=(p['code'], p['temp_setpoint'], p['conveyor_speed'], p.get('notes','')))

    def load_setpoint(self, sp):
        self.ent_sp.delete(0, tk.END)
        self.ent_sp.insert(0, f"{sp}")
        self.at_sp.delete(0, tk.END)
        self.at_sp.insert(0, f"{sp}")

    def load_motor(self, percent):
        self.scale_motor.set(float(percent))

    def clear_form(self):
        for e in (self.txt_code, self.txt_temp, self.txt_speed, self.txt_notes):
            e.delete(0, tk.END)

    def _do_scan(self):
        code = self.txt_scan.get().strip()
        if code and self.cb_on_scan:
            self.cb_on_scan(code)
            self.txt_scan.delete(0, tk.END)

    def _apply_sp(self):
        try:
            sp = float(self.ent_sp.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid", "Setpoint must be a number.")
            return
        if self.cb_on_set_sp:
            self.cb_on_set_sp(sp)
        self.at_sp.delete(0, tk.END)
        self.at_sp.insert(0, f"{sp}")

    def _apply_pid(self):
        try:
            kp = float(self.ent_kp.get().strip()); ki = float(self.ent_ki.get().strip()); kd = float(self.ent_kd.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid", "Kp/Ki/Kd must be numbers.")
            return
        if self.cb_on_set_pid:
            self.cb_on_set_pid(kp, ki, kd)

    def _toggle_enable(self):
        text = self.btn_enable.cget("text")
        ena = (text == "Enable")
        if self.cb_on_enable:
            self.cb_on_enable(ena)
        self.btn_enable.config(text=("Disable" if ena else "Enable"))

    def _on_motor_changed(self, _):
        if self.cb_on_motor:
            self.cb_on_motor(self.scale_motor.get())

    def _on_add(self):
        payload = self._get_form_payload()
        if payload and self.cb_on_add:
            self.cb_on_add(payload)

    def _on_update(self):
        payload = self._get_form_payload()
        if payload and self.cb_on_update:
            self.cb_on_update(payload)

    def _on_delete(self):
        code = self.txt_code.get().strip()
        if code and self.cb_on_delete:
            self.cb_on_delete(code)

    def _get_form_payload(self):
        try:
            return {
                "code": self.txt_code.get().strip(),
                "temp": float(self.txt_temp.get().strip()),
                "speed": float(self.txt_speed.get().strip()),
                "notes": self.txt_notes.get().strip(),
            }
        except ValueError:
            messagebox.showwarning("Invalid", "Temp and Speed must be numbers.")
            return None

    def _at_start(self):
        try:
            params = {
                "enabled": True,
                "relay_high_percent": float(self.at_high.get().strip() or 60.0),
                "relay_low_percent": float(self.at_low.get().strip() or 0.0),
                "hysteresis_c": float(self.at_hyst.get().strip() or 2.0),
                "rule": self.at_rule.get() or "zn_classic",
            }
            sp = float(self.at_sp.get().strip() or self.ent_sp.get().strip())
            if self.cb_on_set_sp:
                self.cb_on_set_sp(sp)
            if self.cb_on_autotune_start:
                self.cb_on_autotune_start(params)
        except ValueError:
            messagebox.showwarning("Auto-tune", "Please enter valid numeric parameters.")

    def _at_stop(self):
        if self.cb_on_autotune_stop:
            self.cb_on_autotune_stop()

    def _at_apply(self):
        if self.cb_on_autotune_apply:
            self.cb_on_autotune_apply()

    
    def show_tuned_gains(self, gains: dict):
            kp, ki, kd = gains.get("Kp"), gains.get("Ki"), gains.get("Kd")
            self.ent_kp.delete(0, tk.END)
            self.ent_kp.insert(0, f"{kp:.4f}")
            self.ent_ki.delete(0, tk.END)
            self.ent_ki.insert(0, f"{ki:.4f}")
            self.ent_kd.delete(0, tk.END)
            self.ent_kd.insert(0, f"{kd:.4f}")
            messagebox.showinfo("Auto-tune", f"Applied tuned gains:\nKp={kp:.4f}\nKi={ki:.4f}\nKd={kd:.4f}")

