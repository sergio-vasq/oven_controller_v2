import tkinter as tk
from tkinter import ttk, messagebox

class SettingsWindow(tk.Toplevel):
    """Technician window: Control (SP, PID) + Auto-tune."""
    def __init__(self, master, initial_sp, initial_kp, initial_ki, initial_kd,
                 on_set_sp, on_set_pid, on_enable,
                 on_autotune_start, on_autotune_stop, on_autotune_apply):
        super().__init__(master)
        self.title("Settings — Control & Auto-tune")
        self.geometry("880x520")
        self.resizable(True, True)

        self.on_set_sp = on_set_sp
        self.on_set_pid = on_set_pid
        self.on_enable = on_enable
        self.on_autotune_start = on_autotune_start
        self.on_autotune_stop = on_autotune_stop
        self.on_autotune_apply = on_autotune_apply

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        # CONTROL
        pnl = ttk.LabelFrame(body, text="Control (PID)")
        pnl.pack(fill="x")
        for i in range(10):
            pnl.columnconfigure(i, weight=1)
        ttk.Label(pnl, text="Setpoint (°C)").grid(row=0, column=0, sticky="w")
        self.ent_sp = ttk.Entry(pnl, width=10)
        self.ent_sp.grid(row=0, column=1, sticky="w")
        self.ent_sp.insert(0, f"{float(initial_sp):.2f}")
        ttk.Button(pnl, text="Apply SP", command=self._apply_sp).grid(row=0, column=2, padx=6, sticky="w")

        ttk.Label(pnl, text="Kp").grid(row=0, column=3, sticky="e"); self.ent_kp = ttk.Entry(pnl, width=10); self.ent_kp.grid(row=0, column=4, sticky="w")
        ttk.Label(pnl, text="Ki").grid(row=0, column=5, sticky="e"); self.ent_ki = ttk.Entry(pnl, width=10); self.ent_ki.grid(row=0, column=6, sticky="w")
        ttk.Label(pnl, text="Kd").grid(row=0, column=7, sticky="e"); self.ent_kd = ttk.Entry(pnl, width=10); self.ent_kd.grid(row=0, column=8, sticky="w")
        self.ent_kp.insert(0, f"{float(initial_kp):.6f}")
        self.ent_ki.insert(0, f"{float(initial_ki):.6f}")
        self.ent_kd.insert(0, f"{float(initial_kd):.6f}")
        ttk.Button(pnl, text="Apply PID", command=self._apply_pid).grid(row=0, column=9, padx=6, sticky="w")

        self.btn_enable = ttk.Button(pnl, text="Enable", command=self._toggle_enable)
        self.btn_enable.grid(row=0, column=10, padx=6, sticky="w")

        # AUTOTUNE
        at = ttk.LabelFrame(body, text="Auto-tune (Relay)")
        at.pack(fill="x", pady=(10,0))
        for i in range(12):
            at.columnconfigure(i, weight=1)
        ttk.Label(at, text="SP (°C)").grid(row=0, column=0, sticky="e"); self.at_sp = ttk.Entry(at, width=10); self.at_sp.grid(row=0, column=1, sticky="w")
        ttk.Label(at, text="High %").grid(row=0, column=2, sticky="e"); self.at_high = ttk.Entry(at, width=8); self.at_high.grid(row=0, column=3, sticky="w")
        ttk.Label(at, text="Low %").grid(row=0, column=4, sticky="e"); self.at_low = ttk.Entry(at, width=8); self.at_low.grid(row=0, column=5, sticky="w")
        ttk.Label(at, text="Hyst (°C)").grid(row=0, column=6, sticky="e"); self.at_hyst = ttk.Entry(at, width=8); self.at_hyst.grid(row=0, column=7, sticky="w")
        ttk.Label(at, text="Rule").grid(row=0, column=8, sticky="e"); self.at_rule = ttk.Combobox(at, values=("zn_classic","zn_no_overshoot","tyreus_luyben"), width=16, state="readonly"); self.at_rule.grid(row=0, column=9, sticky="w")
        self.at_rule.set("zn_classic")

        self.btn_at_start = ttk.Button(at, text="Start Auto-tune", command=self._at_start)
        self.btn_at_start.grid(row=0, column=10, padx=6)
        self.btn_at_stop = ttk.Button(at, text="Stop", command=self._at_stop)
        self.btn_at_stop.grid(row=0, column=11, padx=6)

        res = ttk.Frame(at)
        res.grid(row=1, column=0, columnspan=12, sticky="ew", pady=(6,4))
        for i in range(10):
            res.columnconfigure(i, weight=1)
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

        # Close button
        ttk.Button(body, text="Close", command=self.destroy).pack(pady=10, anchor="e")

    # --- Actions ---
    def _apply_sp(self):
        try:
            sp = float(self.ent_sp.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid", "Setpoint must be a number.")
            return
        if self.on_set_sp:
            self.on_set_sp(sp)
        # Also mirror into autotune SP entry
        self.at_sp.delete(0, tk.END)
        self.at_sp.insert(0, f"{sp}")

    def _apply_pid(self):
        try:
            kp = float(self.ent_kp.get().strip()); ki = float(self.ent_ki.get().strip()); kd = float(self.ent_kd.get().strip())
        except ValueError:
            messagebox.showwarning("Invalid", "Kp/Ki/Kd must be numbers.")
            return
        if self.on_set_pid:
            self.on_set_pid(kp, ki, kd)

    def _toggle_enable(self):
        text = getattr(self, '_enable_text', 'Enable')
        ena = (text == 'Enable')
        if self.on_enable:
            self.on_enable(ena)
        self._enable_text = 'Disable' if ena else 'Enable'
        self.btn_enable.config(text=self._enable_text)

    def _at_start(self):
        try:
            params = {
                "enabled": True,
                "relay_high_percent": float(self.at_high.get().strip() or 60.0),
                "relay_low_percent": float(self.at_low.get().strip() or 0.0),
                "hysteresis_c": float(self.at_hyst.get().strip() or 2.0),
                "rule": self.at_rule.get() or "zn_classic",
            }
            # sync SP
            sp_text = self.at_sp.get().strip() or self.ent_sp.get().strip()
            sp = float(sp_text)
            if self.on_set_sp:
                self.on_set_sp(sp)
            if self.on_autotune_start:
                self.on_autotune_start(params)
        except ValueError:
            messagebox.showwarning("Auto-tune", "Please enter valid numeric parameters.")

    def _at_stop(self):
        if self.on_autotune_stop:
            self.on_autotune_stop()

    def _at_apply(self):
        if self.on_autotune_apply:
            self.on_autotune_apply()

    def show_tuned_gains(self, gains: dict):
        kp, ki, kd = gains.get("Kp"), gains.get("Ki"), gains.get("Kd")
        self.ent_kp.delete(0, tk.END); self.ent_kp.insert(0, f"{kp:.4f}")
        self.ent_ki.delete(0, tk.END); self.ent_ki.insert(0, f"{ki:.4f}")
        self.ent_kd.delete(0, tk.END); self.ent_kd.insert(0, f"{kd:.4f}")
        messagebox.showinfo("Auto-tune", f"Applied tuned gains:\nKp={kp:.4f}\nKi={ki:.4f}\nKd={kd:.4f}")
