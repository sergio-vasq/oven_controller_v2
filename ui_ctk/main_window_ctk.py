import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import time
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PartEditorDialog(ctk.CTkToplevel):
    def __init__(self, master, title, on_save, initial=None):
        super().__init__(master)
        self.title(title)
        self.geometry("440x300")
        self.resizable(False, False)
        self.on_save = on_save

        frm = ctk.CTkFrame(self, corner_radius=8)
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        self.ent_code  = self._labeled_entry(frm, "Código de parte:", 0, width=220)
        self.ent_temp  = self._labeled_entry(frm, "Temperatura (°C):", 1, width=140)
        self.ent_speed = self._labeled_entry(frm, "Velocidad motor (%):", 2, width=140)
        self.ent_notes = self._labeled_entry(frm, "Notas:", 3, width=280)

        btns = ctk.CTkFrame(frm)
        btns.grid(row=4, column=0, columnspan=2, pady=(14,0), sticky="e")
        btn_save   = ctk.CTkButton(btns, text="Guardar",  command=self._save,     width=110)
        btn_cancel = ctk.CTkButton(btns, text="Cancelar", command=self.destroy, width=110)

        btn_cancel.pack(side="left", padx=(0,12))
        btn_save.pack(side="left", padx=(0,0))

        if initial:
            self.ent_code.insert(0, initial.get("code", ""))
            try:
                self.ent_temp.insert(0, f"{float(initial.get('temp', 0)):.2f}")
            except Exception:
                self.ent_temp.insert(0, f"{initial.get('temp', '')}")
            try:
                self.ent_speed.insert(0, f"{float(initial.get('speed', 0)):.2f}")
            except Exception:
                self.ent_speed.insert(0, f"{initial.get('speed', '')}")
            self.ent_notes.insert(0, initial.get("notes", ""))
            self.ent_code.configure(state="disabled")
        else:
            self.ent_code.focus_set()

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()  # modal

    def _labeled_entry(self, parent, label, row, width=160):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(2,8))
        ent = ctk.CTkEntry(parent, width=width)
        ent.grid(row=row, column=1, sticky="w")
        return ent

    def _save(self):
        try:
            code  = self.ent_code.get().strip()
            temp_text = self.ent_temp.get().strip()
            speed_text = self.ent_speed.get().strip()
            notes = self.ent_notes.get().strip()
            if not code:
                raise ValueError("El código de parte es obligatorio.")
            temp  = float(temp_text)
            speed = float(speed_text)
        except ValueError as e:
            messagebox.showwarning("Dato inválido", str(e))
            return
        if self.on_save:
            self.on_save({"code": code, "temp": temp, "speed": speed, "notes": notes})
        self.destroy()


class TemperaturePlot(ctk.CTkFrame):
    def __init__(self, master, window_seconds=600, redraw_ms=400):
            super().__init__(master)
            self.window_s = float(window_seconds)
            self.redraw_ms = int(redraw_ms)
            self.data = deque()

            # << Nuevo: guarda estado de tema >>
            self._appearance = "Dark"

            # Inicializa con tema oscuro por defecto (puedes cambiarlo luego con set_theme)
            self._init_figure_for_theme(self._appearance)

            self.canvas = FigureCanvasTkAgg(self.fig, master=self)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)

            self.after(self.redraw_ms, self._redraw_timer)


    def _init_figure_for_theme(self, appearance: str):
        dark = str(appearance).lower().startswith("dark")
        bg    = "#2b2b2b" if dark else "#ffffff"
        fg    = "#ffffff" if dark else "#000000"
        grid  = "#666666" if dark else "#cccccc"
        pv_c  = "#4aa3ff" if dark else "#1f77b4"   # serie PV
        sp_c  = "#ffae42" if dark else "#ff7f0e"   # serie SP

        if not hasattr(self, "fig"):
            from matplotlib.figure import Figure
            self.fig = Figure(figsize=(6, 2.8), dpi=100)
            self.ax = self.fig.add_subplot(111)
            (self.line_pv,) = self.ax.plot([], [], label="PV", color=pv_c, linewidth=1.6)
            (self.line_sp,) = self.ax.plot([], [], label="SP", color=sp_c, linewidth=1.3)
        else:
            self.line_pv.set_color(pv_c)
            self.line_sp.set_color(sp_c)

        self.fig.patch.set_facecolor(bg)
        self.ax.set_facecolor(bg)
        self.ax.set_title("Temperaturas (PV / SP)", color=fg)
        self.ax.set_xlabel("Tiempo (min)", color=fg)
        self.ax.set_ylabel("°C", color=fg)
        self.ax.tick_params(colors=fg)
        for spine in self.ax.spines.values():
            spine.set_color(fg)
        self.ax.grid(True, color=grid, alpha=0.4)

        leg = self.ax.legend(loc="upper right")
        for text in leg.get_texts():
            text.set_color(fg)
        leg.get_frame().set_facecolor("#1f1f1f" if dark else "#f3f3f3")
        leg.get_frame().set_edgecolor(grid)

    def set_theme(self, appearance: str):
        self._appearance = appearance
        self._init_figure_for_theme(appearance)
        self.canvas.draw_idle()


    def append(self, pv, sp):
        now = time.time()
        self.data.append((now, pv, sp))
        cutoff = now - self.window_s
        while self.data and self.data[0][0] < cutoff:
            self.data.popleft()

    def _redraw_timer(self):
        self._draw_plot()
        self.after(self.redraw_ms, self._redraw_timer)

    # Renamed to not collide with CTkFrame._draw(...)
    def _draw_plot(self):
        if not self.data:
            return
        t0 = self.data[0][0]
        xs = [(t - t0) / 60.0 for (t, _pv, _sp) in self.data]

        pv_series, sp_series = [], []
        last_pv, last_sp = None, None
        for (_t, pv, sp) in self.data:
            last_pv = pv if pv is not None else last_pv
            last_sp = sp if sp is not None else last_sp
            pv_series.append(last_pv if last_pv is not None else 0.0)
            sp_series.append(last_sp if last_sp is not None else 0.0)

        self.line_pv.set_data(xs, pv_series)
        self.line_sp.set_data(xs, sp_series)

        # Y limits
        if pv_series:
            ymin = min(pv_series + sp_series) - 5
            ymax = max(pv_series + sp_series) + 5
            if ymin == ymax:
                ymin -= 1
                ymax += 1
            self.ax.set_ylim(ymin, ymax)

        # X limits (fix singular xlim warning)
        if xs:
            xmax = max(xs)
            if xmax <= 0:
                xmax = 1.0  # ensure min width
            self.ax.set_xlim(0, xmax)
        else:
            self.ax.set_xlim(0, 10)

        self.canvas.draw_idle()


class MainWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0)
        self.pack(fill="both", expand=True)
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        # ----- Dark style for ttk.Treeview
        style = ttk.Style()
        try:
            style.theme_use('default')
        except Exception:
            pass

        font_rows = ("Segoe UI", 12)
        font_head = ("Segoe UI", 12, "bold")

        style.configure(
            "Dark.Treeview",
            background="black",
            foreground="white",
            fieldbackground="black",
            rowheight=28,
            font=font_rows,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", "#094771")],
            foreground=[("selected", "white")]
        )
        style.configure(
            "Dark.Treeview.Heading",
            background="#111111",
            foreground="white",
            relief="flat",
            font=font_head,
        )

        # ----- Toolbar
        bar = ctk.CTkFrame(self)
        bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,6))
        bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(bar, text="Oven Controller CSC", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")
        self.btn_settings = ctk.CTkButton(bar, text="Configuración", command=self._open_settings)
        self.btn_settings.grid(row=0, column=2, sticky="e", padx=(8,0))

        # ----- Status
        status = ctk.CTkFrame(self)
        status.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        for i in range(6):
            status.grid_columnconfigure(i, weight=1)
        self.lbl_sp    = ctk.CTkLabel(status, text="SP: — °C")
        self.lbl_pv    = ctk.CTkLabel(status, text="PV: — °C")
        self.lbl_u     = ctk.CTkLabel(status, text="Calentador: — %")
        self.lbl_motor = ctk.CTkLabel(status, text="Motor: — %")
        self.lbl_mode  = ctk.CTkLabel(status, text="Modo: DESHABILITADO")
        self.lbl_alarm = ctk.CTkLabel(status, text="Alarma: —")
        for i, w in enumerate((self.lbl_sp, self.lbl_pv, self.lbl_u, self.lbl_motor, self.lbl_mode, self.lbl_alarm)):
            w.grid(row=0, column=i, padx=8, pady=6, sticky="w")

        # ----- Scan
        scan = ctk.CTkFrame(self)
        scan.grid(row=2, column=0, sticky="ew", padx=10, pady=(0,6))
        scan.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(scan, text="Escanear / Capturar código de parte").grid(row=0, column=0, sticky="w", padx=(0,8))
        self.txt_scan = ctk.CTkEntry(scan)
        self.txt_scan.grid(row=0, column=1, sticky="ew")
        self.txt_scan.bind("<Return>", lambda e: self._do_scan())
        self._enable_global_scanner_capture(root=self.master)

        # ----- Plot
        self.plot = TemperaturePlot(self, window_seconds=600, redraw_ms=400)  # 10 min
        self.plot.grid(row=3, column=0, sticky="nsew", padx=10, pady=6)

        # ----- Library + actions
        lib = ctk.CTkFrame(self)
        lib.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0,10))
        lib.grid_rowconfigure(0, weight=1)
        lib.grid_columnconfigure(0, weight=1)

        self.table = ttk.Treeview(lib, columns=("code","temp","speed","notes"), show="headings", height=8, style="Dark.Treeview")
        for c, txt, w in (("code","Código",220),("temp","Temp (°C)",140),("speed","Velocidad (%)",160),("notes","Notas",500)):
            self.table.heading(c, text=txt)
            self.table.column(c, width=w, anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew")

        # Scrollbar
        yscroll = ttk.Scrollbar(lib, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")

        # Buttons
        btns = ctk.CTkFrame(lib)
        btns.grid(row=1, column=0, sticky="w", pady=(8,0))

        self.btn_new    = ctk.CTkButton(btns, text="Nuevo",    command=self._on_new)
        self.btn_edit   = ctk.CTkButton(btns, text="Editar",   command=self._on_edit,   state="disabled")
        self.btn_delete = ctk.CTkButton(btns, text="Eliminar", command=self._on_delete, state="disabled")

        self.btn_new.pack(side="left", padx=(0, 8))
        self.btn_edit.pack(side="left", padx=(0, 8))
        self.btn_delete.pack(side="left", padx=(0, 0))

        # Enable/disable edit/delete depending on selection
        self.table.bind("<<TreeviewSelect>>", lambda e: self._toggle_actions())

        # Expand
        self.grid_rowconfigure(3, weight=1)  # plot
        self.grid_rowconfigure(4, weight=1)  # table
        self.grid_columnconfigure(0, weight=1)

        # External callbacks
        self.cb_on_scan = None
        self.cb_on_new = None
        self.cb_on_edit = None
        self.cb_on_delete = None
        self.cb_on_open_settings = None

        # Shortcuts
        self.master.bind("<Control-n>", lambda e: self._on_new())
        self.master.bind("<Control-e>", lambda e: self._on_edit())
        self.master.bind("<Delete>",    lambda e: self._on_delete())

    # Bind callbacks (keep English names for app.py compatibility)
    def bind_callbacks(self, on_scan, on_new, on_edit, on_delete, on_open_settings):
        self.cb_on_scan = on_scan
        self.cb_on_new = on_new
        self.cb_on_edit = on_edit
        self.cb_on_delete = on_delete
        self.cb_on_open_settings = on_open_settings

    # Controller update funnel
    def handle_update(self, data: dict):
        self.update_status(data)
        sp = data.get("sp", None)
        pv = data.get("pv", None)
        if pv is not None or sp is not None:
            self.plot.append(pv, sp)

    # UI helpers 
    def update_status(self, data: dict):
        sp = data.get("sp")
        pv = data.get("pv")
        u  = data.get("u")
        mot = data.get("motor")
        ena = data.get("enabled")
        alarm = data.get("alarm")
        self.lbl_sp.configure(text=f"SP: {sp:.1f} °C" if sp is not None else "SP: — °C")
        self.lbl_pv.configure(text=f"PV: {pv:.1f} °C" if pv is not None else "PV: — °C")
        self.lbl_u.configure(text=f"Calentador: {u:.1f} %")
        self.lbl_motor.configure(text=f"Motor: {mot:.1f} %")
        self.lbl_mode.configure(text=f"Modo: {'HABILITADO' if ena else 'DESHABILITADO'}")
        self.lbl_alarm.configure(text=f"Alarma: {alarm if alarm else '—'}")

    def load_parts(self, parts):
        for iid in self.table.get_children():
            self.table.delete(iid)
        for p in parts:
            self.table.insert('', 'end', values=(p['code'], p['temp_setpoint'], p['conveyor_speed'], p.get('notes','')))
        self._toggle_actions()

    def load_setpoint(self, sp):
        self.lbl_sp.configure(text=f"SP: {float(sp):.1f} °C")

    # Events
    def _do_scan(self):
        code = self.txt_scan.get().strip()
        if code and self.cb_on_scan:
            self.cb_on_scan(code)
            self.txt_scan.delete(0, tk.END)

    def _get_selected_row(self):
        sel = self.table.selection()
        if not sel:
            return None
        vals = self.table.item(sel[0], "values")
        try:
            return {
                "code": vals[0],
                "temp": float(vals[1]),
                "speed": float(vals[2]),
                "notes": vals[3],
            }
        except Exception:
            return {
                "code": vals[0],
                "temp": vals[1],
                "speed": vals[2],
                "notes": vals[3],
            }

    def _on_new(self):
        def save(payload):
            if self.cb_on_new:
                self.cb_on_new(payload)
        PartEditorDialog(self, "Nueva parte", on_save=save, initial=None)

    def _on_edit(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("Editar", "Selecciona una parte primero.")
            return
        def save(payload):
            if self.cb_on_edit:
                self.cb_on_edit(payload)
        PartEditorDialog(self, f"Editar parte — {row['code']}", on_save=save, initial=row)

    def _on_delete(self):
        row = self._get_selected_row()
        if not row:
            messagebox.showinfo("Eliminar", "Selecciona una parte primero.")
            return
        if messagebox.askyesno("Eliminar", f"¿Eliminar la parte '{row['code']}'?"):
            if self.cb_on_delete:
                self.cb_on_delete(row["code"])

    def _open_settings(self):
        if self.cb_on_open_settings:
            self.cb_on_open_settings()

    def _toggle_actions(self):
        has_sel = bool(self.table.selection())
        state = "normal" if has_sel else "disabled"
        self.btn_edit.configure(state=state)
        self.btn_delete.configure(state=state)

    def apply_treeview_style(self, appearance: str):
        """Aplica estilos al Treeview en función del tema."""
        dark = str(appearance).lower().startswith("dark")
        style = ttk.Style()

        tv_style_name = "Dark.Treeview" if dark else "Light.Treeview"
        tv_head_name  = "Dark.Treeview.Heading" if dark else "Light.Treeview.Heading"

        bg = "black" if dark else "white"
        fg = "white" if dark else "black"
        sel_bg = "#094771" if dark else "#cce5ff"
        sel_fg = "white" if dark else "black"
        head_bg = "#111111" if dark else "#f0f0f0"
        head_fg = "white" if dark else "black"

        font_rows = ("Segoe UI", 12)
        font_head = ("Segoe UI", 12, "bold")

        style.configure(
            tv_style_name,
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=28,
            font=font_rows,
        )
        style.map(
            tv_style_name,
            background=[("selected", sel_bg)],
            foreground=[("selected", sel_fg)],
        )
        style.configure(
            tv_head_name,
            background=head_bg,
            foreground=head_fg,
            relief="flat",
            font=font_head,
        )

        self.table.configure(style=tv_style_name)

    def apply_theme(self, appearance: str):
        self.plot.set_theme(appearance)
        self.apply_treeview_style(appearance)

    def _enable_global_scanner_capture(self, root):
        root.bind_all("<Key>", self._global_key_reroute, add="+")
        self._kb_capture_enabled = True

    def _is_textual_widget(self, widget):
        import tkinter as tk
        from tkinter import ttk
        text_like = (tk.Entry, tk.Text, ttk.Entry)
        try:
            import customtkinter as ctk
            text_like = text_like + (ctk.CTkEntry, )
        except Exception:
            pass
        return isinstance(widget, text_like)

    def _keysym_to_char(self, event):
        if event.char and event.char.isprintable():
            return event.char

        ks = event.keysym
        keypad_map = {
            "KP_0":"0","KP_1":"1","KP_2":"2","KP_3":"3","KP_4":"4",
            "KP_5":"5","KP_6":"6","KP_7":"7","KP_8":"8","KP_9":"9",
            "KP_Decimal":".","KP_Separator":",","KP_Multiply":"*","KP_Divide":"/",
            "KP_Add":"+","KP_Subtract":"-","KP_Enter":"\r","KP_Space":" ",
        }
        return keypad_map.get(ks, "")

    def _global_key_reroute(self, event):
        if (event.state & 0x4) or (event.state & 0x200000) or event.keysym in (
            "Shift_L","Shift_R","Control_L","Control_R","Alt_L","Alt_R","Meta_L","Meta_R"
        ):
            return  # deja pasar atajos

        w = event.widget
        if self._is_textual_widget(w):
            return  # deja que escriba donde está

        if event.keysym in ("BackSpace",):
            self.txt_scan.focus_set()
            # Reenvía el BackSpace al Entry
            self.txt_scan.event_generate("<BackSpace>")
            return "break"

        if event.keysym in ("Return", "KP_Enter"):
            # Ejecuta tu scan
            self._do_scan()
            return "break"

        ch = (event.char or "").strip()
        if not ch:
            ch = self._keysym_to_char(event)

        if ch and ch.isprintable():
            self.txt_scan.focus_set()
            self.txt_scan.insert("end", ch)
            return "break"

        return