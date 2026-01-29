import tkinter as tk
from tkinter import ttk, messagebox

class MainWindow(ttk.Frame):
    """Operator UI: Status, Scan, Library, CRUD, and a Settings button."""
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.master = master
        self.master.title("Oven Controller V2")
        self.master.geometry("1000x640")
        self.grid(sticky="nsew")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # Menu/Toolbar area
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(toolbar, text="Oven Controller").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        self.btn_settings = ttk.Button(toolbar, text="Settings", command=self._open_settings)
        self.btn_settings.grid(row=0, column=1, padx=6)
        toolbar.columnconfigure(2, weight=1)

        # STATUS
        status = ttk.LabelFrame(self, text="Status")
        status.grid(row=1, column=0, sticky="ew")
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

        # SCAN
        scan = ttk.LabelFrame(self, text="Scan / Enter Part Code")
        scan.grid(row=2, column=0, sticky="ew", pady=(8,0))
        scan.columnconfigure(0, weight=1)
        self.txt_scan = ttk.Entry(scan)
        self.txt_scan.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        self.txt_scan.bind("<Return>", lambda e: self._do_scan())

        # LIBRARY
        lib = ttk.LabelFrame(self, text="Part Library")
        lib.grid(row=3, column=0, sticky="nsew", pady=(8,0))
        lib.rowconfigure(0, weight=1)
        lib.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(lib, columns=("code","temp","speed","notes"), show="headings")
        for c, txt, w in (("code","Code",180),("temp","Temp (°C)",120),("speed","Speed",120),("notes","Notes",300)):
            self.table.heading(c, text=txt)
            self.table.column(c, width=w, anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew")

        # CRUD
        frm = ttk.Frame(self)
        frm.grid(row=4, column=0, sticky="ew", pady=8)
        ttk.Label(frm, text="Code").grid(row=0, column=0, padx=(0,4), sticky="w"); self.txt_code = ttk.Entry(frm, width=24); self.txt_code.grid(row=0, column=1, padx=(0,12))
        ttk.Label(frm, text="Temp °C").grid(row=0, column=2, padx=(0,4), sticky="w"); self.txt_temp = ttk.Entry(frm, width=12); self.txt_temp.grid(row=0, column=3, padx=(0,12))
        ttk.Label(frm, text="Speed").grid(row=0, column=4, padx=(0,4), sticky="w"); self.txt_speed = ttk.Entry(frm, width=12); self.txt_speed.grid(row=0, column=5, padx=(0,12))
        ttk.Label(frm, text="Notes").grid(row=0, column=6, padx=(0,4), sticky="w"); self.txt_notes = ttk.Entry(frm, width=30); self.txt_notes.grid(row=0, column=7, padx=(0,12))
        ttk.Button(frm, text="Add", command=self._on_add).grid(row=0, column=8, padx=6)
        ttk.Button(frm, text="Update", command=self._on_update).grid(row=0, column=9, padx=6)
        ttk.Button(frm, text="Delete", command=self._on_delete).grid(row=0, column=10, padx=6)

        self.rowconfigure(3, weight=1)

        # External callbacks
        self.cb_on_scan = None
        self.cb_on_add = None
        self.cb_on_update = None
        self.cb_on_delete = None
        self.cb_on_open_settings = None

    def bind_callbacks(self, on_scan, on_add, on_update, on_delete, on_open_settings):
        self.cb_on_scan = on_scan
        self.cb_on_add = on_add
        self.cb_on_update = on_update
        self.cb_on_delete = on_delete
        self.cb_on_open_settings = on_open_settings

    # --- UI helpers ---
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

    def load_parts(self, parts):
        for iid in self.table.get_children():
            self.table.delete(iid)
        for p in parts:
            self.table.insert('', 'end', values=(p['code'], p['temp_setpoint'], p['conveyor_speed'], p.get('notes','')))

    def load_setpoint(self, sp):
        self.lbl_sp.config(text=f"SP: {float(sp):.1f} °C")

    def clear_form(self):
        for e in (self.txt_code, self.txt_temp, self.txt_speed, self.txt_notes):
            e.delete(0, tk.END)

    # --- Events ---
    def _do_scan(self):
        code = self.txt_scan.get().strip()
        if code and self.cb_on_scan:
            self.cb_on_scan(code)
            self.txt_scan.delete(0, tk.END)

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

    def _open_settings(self):
        if self.cb_on_open_settings:
            self.cb_on_open_settings()

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
