import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, initial_sp, initial_kp, initial_ki, initial_kd,
                 on_set_sp, on_set_pid, on_enable,
                 on_autotune_start, on_autotune_stop, on_autotune_apply):
        super().__init__(master)
        self.title("Configuración — Control y Autoajuste")
        self.geometry("380x600")   
        self.resizable(True, True)

        # External callbacks
        self.on_set_sp = on_set_sp
        self.on_set_pid = on_set_pid
        self.on_enable = on_enable
        self.on_autotune_start = on_autotune_start
        self.on_autotune_stop = on_autotune_stop
        self.on_autotune_apply = on_autotune_apply

        # Internal state for toggles
        self._control_enabled = False
        self._autotune_running = False

        # Root body
        body = ctk.CTkScrollableFrame(self, corner_radius=8)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)

        # ========== Section: CONTROL (SP & PID) ==========
        section_ctrl = ctk.CTkFrame(body, fg_color="transparent")
        section_ctrl.grid(row=0, column=0, sticky="w")
        section_ctrl.grid_columnconfigure(0, weight=1)

        ctrl_title = ctk.CTkLabel(section_ctrl, text="Control (SP y PID)",font=ctk.CTkFont(size=15, weight="bold"))
        ctrl_title.grid(row=0, column=0, sticky="w", padx=(4,4), pady=(2,2))

        ctrl_sep = ctk.CTkFrame(section_ctrl, height=2, fg_color="#444444")
        ctrl_sep.grid(row=1, column=0, sticky="ew", padx=0, pady=(0,8))

        # Grid 3 columnas: (0) label, (1) entry/display (expand), (2) button
        ctrl = ctk.CTkFrame(section_ctrl)
        ctrl.grid(row=2, column=0, sticky="w")
        ctrl.grid_columnconfigure(0, weight=0, minsize=120)
        ctrl.grid_columnconfigure(1, weight=1, minsize=120)
        ctrl.grid_columnconfigure(2, weight=0, minsize=120)

        # Row 0: Setpoint (°C) | Entry | Aplicar SP
        ctk.CTkLabel(ctrl, text="Setpoint (°C)").grid(row=0, column=0, sticky="w", padx=(6,6), pady=(6,6))
        self.ent_sp = ctk.CTkEntry(ctrl, width=100)
        self.ent_sp.grid(row=0, column=1, sticky="w", padx=(0,8), pady=(6,6))
        self.ent_sp.insert(0, f"{float(initial_sp):.2f}")
        ctk.CTkButton(ctrl, text="Aplicar SP", command=self._apply_sp, width=100)\
            .grid(row=0, column=2, sticky="w", padx=(0,6), pady=(6,6))

        # Row 1: Kp | Entry | —
        ctk.CTkLabel(ctrl, text="Kp").grid(row=1, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.ent_kp = ctk.CTkEntry(ctrl, width=100)
        self.ent_kp.grid(row=1, column=1, sticky="w", padx=(0,8), pady=(4,6))
        self.ent_kp.insert(0, f"{float(initial_kp):.6f}")

        # Row 2: Ki | Entry | —
        ctk.CTkLabel(ctrl, text="Ki").grid(row=2, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.ent_ki = ctk.CTkEntry(ctrl, width=100)
        self.ent_ki.grid(row=2, column=1, sticky="w", padx=(0,8), pady=(4,6))
        self.ent_ki.insert(0, f"{float(initial_ki):.6f}")

        # Row 3: Kd | Entry | Aplicar PID
        ctk.CTkLabel(ctrl, text="Kd").grid(row=3, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.ent_kd = ctk.CTkEntry(ctrl, width=100)
        self.ent_kd.grid(row=3, column=1, sticky="w", padx=(0,8), pady=(4,6))
        self.ent_kd.insert(0, f"{float(initial_kd):.6f}")
        ctk.CTkButton(ctrl, text="Aplicar PID", command=self._apply_pid, width=100)\
            .grid(row=3, column=2, sticky="w", padx=(0,6), pady=(4,6))

        # Row 4: — | [Toggle Habilitar/Deshabilitar] | —
        self.btn_enable = ctk.CTkButton(ctrl, text="Habilitar",command=self._toggle_enable, width=100)
        self.btn_enable.grid(row=4, column=1, sticky="w", padx=(0,0), pady=(8,6))

        # ========== Section: PID Auto-Tunning ==========
        section_at = ctk.CTkFrame(body, fg_color="transparent")
        section_at.grid(row=1, column=0, sticky="w", pady=(10,0))
        section_at.grid_columnconfigure(0, weight=1)

        at_title = ctk.CTkLabel(section_at, text="PID Auto-Tunning",font=ctk.CTkFont(size=15, weight="bold"))
        at_title.grid(row=0, column=0, sticky="w", padx=(4,4), pady=(2,2))

        at_sep = ctk.CTkFrame(section_at, height=2, fg_color="#444444")
        at_sep.grid(row=1, column=0, sticky="ew", padx=0, pady=(0,8))

        at = ctk.CTkFrame(section_at)
        at.grid(row=2, column=0, sticky="w")
        at.grid_columnconfigure(0, weight=0, minsize=120)  # label
        at.grid_columnconfigure(1, weight=1, minsize=120)  # editor/display

        r = 0
        # Parameters (SP, % Alto, % Bajo, Hist, Regla)
        ctk.CTkLabel(at, text="SP (°C)").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.at_sp = ctk.CTkEntry(at, width=100)
        self.at_sp.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(4,6)); r += 1

        ctk.CTkLabel(at, text="% Alto").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.at_high = ctk.CTkEntry(at, width=100)
        self.at_high.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(4,6)); r += 1

        ctk.CTkLabel(at, text="% Bajo").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.at_low = ctk.CTkEntry(at, width=100)
        self.at_low.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(4,6)); r += 1

        ctk.CTkLabel(at, text="Hist (°C)").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(4,6))
        self.at_hyst = ctk.CTkEntry(at, width=100)
        self.at_hyst.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(4,6)); r += 1

        ctk.CTkLabel(at, text="Regla").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(4,10))
        self.at_rule = ctk.CTkComboBox(at, values=("zn_classic","zn_no_overshoot","tyreus_luyben"), width=100)
        self.at_rule.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(4,10))
        self.at_rule.set("zn_classic"); r += 1

        # Toggle auto-tune (single button, centered in column 1)
        self.btn_at_toggle = ctk.CTkButton(at, text="Iniciar autoajuste",command=self._toggle_autotune, width=100)
        self.btn_at_toggle.grid(row=r, column=1, sticky="w", padx=(0,0), pady=(4,12)); r += 1

        # Results (each in its own row: label in col 0, value in col 1)
        ctk.CTkLabel(at, text="Ciclos").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,4))
        self.lbl_cycles_val = ctk.CTkLabel(at, text="0")
        self.lbl_cycles_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,4)); r += 1

        # Row: Ku
        ctk.CTkLabel(at, text="Ku").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,4))
        self.lbl_ku_val = ctk.CTkLabel(at, text="—")
        self.lbl_ku_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,4)); r += 1

        # Row: Tu
        ctk.CTkLabel(at, text="Tu").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,4))
        self.lbl_tu_val = ctk.CTkLabel(at, text="— s")
        self.lbl_tu_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,4)); r += 1

        # Row: Kp
        ctk.CTkLabel(at, text="Kp").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,4))
        self.lbl_kp_val = ctk.CTkLabel(at, text="—")
        self.lbl_kp_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,4)); r += 1

        # Row: Ki
        ctk.CTkLabel(at, text="Ki").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,4))
        self.lbl_ki_val = ctk.CTkLabel(at, text="—")
        self.lbl_ki_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,4)); r += 1

        # Row: Kd + Apply button (col 3)
        ctk.CTkLabel(at, text="Kd").grid(row=r, column=0, sticky="w", padx=(6,6), pady=(2,8))
        self.lbl_kd_val = ctk.CTkLabel(at, text="—")
        self.lbl_kd_val.grid(row=r, column=1, sticky="w", padx=(0,8), pady=(2,8)); r += 1
        ctk.CTkButton(at, text="Aplicar ganancias sintonizadas",command=self._at_apply, width=100)\
            .grid(row=r, column=1, sticky="w", padx=(0,6), pady=(2,8))
        r += 1

        # Close on ESC
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    # =========================
    # Actions / Public methods
    # =========================
    def _apply_sp(self):
        try:
            sp = float(self.ent_sp.get().strip())
        except ValueError:
            messagebox.showwarning("Dato inválido", "El setpoint debe ser numérico.")
            return
        if self.on_set_sp:
            self.on_set_sp(sp)
        # mirror into autotune SP
        self.at_sp.delete(0, tk.END)
        self.at_sp.insert(0, f"{sp}")

    def _apply_pid(self):
        try:
            kp = float(self.ent_kp.get().strip())
            ki = float(self.ent_ki.get().strip())
            kd = float(self.ent_kd.get().strip())
        except ValueError:
            messagebox.showwarning("Dato inválido", "Kp, Ki y Kd deben ser numéricos.")
            return
        if self.on_set_pid:
            self.on_set_pid(kp, ki, kd)

    def _toggle_enable(self):
        enable = not self._control_enabled
        if self.on_enable:
            self.on_enable(enable)
        self._control_enabled = enable
        self.btn_enable.configure(text="Deshabilitar" if enable else "Habilitar")

    def _toggle_autotune(self):
        """Single button to start/stop autotune."""
        if not self._autotune_running:
            # Start
            try:
                params = {
                    "enabled": True,
                    "relay_high_percent": float(self.at_high.get().strip() or 60.0),
                    "relay_low_percent": float(self.at_low.get().strip() or 0.0),
                    "hysteresis_c": float(self.at_hyst.get().strip() or 2.0),
                    "rule": self.at_rule.get() or "zn_classic",
                }
                sp_text = self.at_sp.get().strip() or self.ent_sp.get().strip()
                sp = float(sp_text)
                if self.on_set_sp:
                    self.on_set_sp(sp)
                if self.on_autotune_start:
                    self.on_autotune_start(params)
                self._autotune_running = True
                self.btn_at_toggle.configure(text="Detener autoajuste")
            except ValueError:
                messagebox.showwarning("Autoajuste", "Verifica que los parámetros sean numéricos.")
        else:
            # Stop
            if self.on_autotune_stop:
                self.on_autotune_stop()
            self._autotune_running = False
            self.btn_at_toggle.configure(text="Iniciar autoajuste")

    def _at_start(self):
        if not self._autotune_running:
            self._toggle_autotune()

    def _at_stop(self):
        if self._autotune_running:
            self._toggle_autotune()

    def _at_apply(self):
        if self.on_autotune_apply:
            self.on_autotune_apply()

    def show_tuned_gains(self, gains: dict):
        """Show tuned gains in results (and copy into PID entries if desired)."""
        kp, ki, kd = gains.get("Kp"), gains.get("Ki"), gains.get("Kd")
        # Update the PID entries so user can review them
        self.ent_kp.delete(0, tk.END); self.ent_kp.insert(0, f"{kp:.4f}")
        self.ent_ki.delete(0, tk.END); self.ent_ki.insert(0, f"{ki:.4f}")
        self.ent_kd.delete(0, tk.END); self.ent_kd.insert(0, f"{kd:.4f}")
        # Update the results labels
        self.lbl_kp_val.configure(text=f"{kp:.4f}")
        self.lbl_ki_val.configure(text=f"{ki:.4f}")
        self.lbl_kd_val.configure(text=f"{kd:.4f}")
        messagebox.showinfo("Autoajuste", f"Ganancias aplicadas:\nKp={kp:.4f}\nKi={ki:.4f}\nKd={kd:.4f}")