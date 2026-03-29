# app.py
import sys
import yaml
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from customtkinter import CTkInputDialog

from data.storage import Storage
from services.controller import ControllerV2
from ui_ctk.main_window_ctk import MainWindow
from ui_ctk.settings_window_ctk import SettingsWindow

from devices.thermocouple_max6675 import MAX6675
from devices.ssr_timeproportion import SSRTimeProportion
from devices.step_motor_clock import StepMotorClock
from devices.fan_gpio import FanGPIO
from devices.gpio_button import GPIOButton

try:
    from barcode.scanner_serial import SerialBarcodeScanner
except Exception:
    SerialBarcodeScanner = None

CONFIG_PATH = Path("config.yaml")

def save_tuned_gains_to_config(kp: float, ki: float, kd: float):
    try:
        cfg = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r") as f:
                cfg = yaml.safe_load(f) or {}
        cfg.setdefault("pid", {})
        cfg["pid"]["kp"] = float(kp)
        cfg["pid"]["ki"] = float(ki)
        cfg["pid"]["kd"] = float(kd)
        with open(CONFIG_PATH, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        return True, "Saved tuned gains to config.yaml"
    except Exception as e:
        return False, f"Failed to save config: {e}"

def _load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {
        "pid": {
            "kp": 10.0,
            "ki": 1.0,
            "kd": 0.0,
            "sample_seconds": 0.5,
            "output_limits": [0.0, 100.0],
        },
        "ui": {
            "appearance": "Dark",
            "theme": "blue",
            "geometry": "1100x720",
        },
    }

def main():
    cfg = _load_config()
    storage = Storage()

    tc = None
    ssr = None
    motor = None
    fan = None
    stop_btn = None

    # Thermocouple
    try:
        th_cfg = cfg.get("thermocouple", {})
        if th_cfg:
            tc = MAX6675(
                spi_device=th_cfg["spi_device"],
                mode=int(th_cfg.get("spi_mode", 0)),
                max_hz=int(th_cfg.get("spi_max_hz", 4000000)),
                samples_avg=max(1, int(th_cfg.get("samples_avg", 1))),
            )
    except Exception as e:
        print(f"[WARN] MAX6675 not available: {e}")

    # SSR
    try:
        ssr_cfg = cfg.get("ssr", {})
        if ssr_cfg:
            ssr = SSRTimeProportion(
                gpio_chip=ssr_cfg["gpio_chip"],
                gpio_line=int(ssr_cfg["gpio_line"]),
                active_high=bool(ssr_cfg.get("active_high", True)),
                window_s=float(ssr_cfg.get("window_seconds", 1.0)),
            )
    except Exception as e:
        print(f"[WARN] SSR GPIO not available: {e}")

    # Motor
    try:
        motor_cfg = cfg.get("motor", {})
        if motor_cfg:
            motor = StepMotorClock(cfg)
    except Exception as e:
        print(f"[WARN] Motor PWM not available: {e}")

    # FAN
    try:
        fan_cfg = cfg.get("fan", {})
        if fan_cfg:
            fan = FanGPIO(
                gpio_chip=fan_cfg["gpio_chip"],
                gpio_line=int(fan_cfg["gpio_line"]),
                active_high=bool(fan_cfg.get("active_high", True)),
                default_on=bool(fan_cfg.get("default_on", False)),
            )
    except Exception as e:
        print(f"[WARN] Fan GPIO not available: {e}")

    # UI
    ui_cfg = cfg.get("ui", {})
    settings_password = str(ui_cfg.get("settings_password", "0707"))
    ctk.set_appearance_mode(ui_cfg.get("appearance", "Dark"))
    ctk.set_default_color_theme(ui_cfg.get("theme", "blue"))
    root = ctk.CTk()
    root.title("Oven Controller CSC")
    geometry = ui_cfg.get("geometry", "1100x720")
    try:
        root.geometry(geometry)
    except Exception:
        root.geometry("1100x720")

    win = MainWindow(root)
    appearance = ui_cfg.get("appearance", "Dark")
    win.apply_theme(appearance)

    # Controller
    pid_cfg = cfg.get("pid", {})
    saf_cfg = cfg.get("safety", {})
    at_cfg = cfg.get("autotune", {})

    controller = ControllerV2(
        thermocouple=tc,
        heater=ssr,
        motor=motor,
        storage=storage,
        kp=float(pid_cfg.get("kp", 10.0)),
        ki=float(pid_cfg.get("ki", 1.0)),
        kd=float(pid_cfg.get("kd", 0.0)),
        sample_s=float(pid_cfg.get("sample_seconds", 0.5)),
        output_limits=tuple(pid_cfg.get("output_limits", [0.0, 100.0])),
        safety_cfg=saf_cfg,
        autotune_cfg=at_cfg,
        on_update=lambda data: root.after(0, win.handle_update, data),
        fan=fan,
    )

    # --- Callbacks del catálogo/scan ---
    def apply_part(code: str):
        ok, part = controller.apply_part(code)
        if not ok:
            messagebox.showwarning("Not found", f"Part code '{code}' not found.")
        else:
            win.load_setpoint(part["temp_setpoint"])
            win.load_parts(storage.list_parts())

    def ui_add(payload):
        try:
            storage.add_part(payload["code"], payload["temp"], payload["speed"], payload.get("notes", ""))
            win.load_parts(storage.list_parts())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add: {e}")

    def ui_update(payload):
        try:
            storage.update_part(payload["code"], payload["temp"], payload["speed"], payload.get("notes", ""))
            win.load_parts(storage.list_parts())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")

    def ui_delete(code):
        try:
            storage.delete_part(code)
            win.load_parts(storage.list_parts())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    # Settings window
    settings_win_ref = {"obj": None}

    def open_settings_request():
        dlg = CTkInputDialog(text="Introduce la contraseña de Configuración:", title="Protegido")
        pwd = dlg.get_input()
        if pwd is None:
            return
        if str(pwd).strip() != settings_password:
            messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")
            return

        if settings_win_ref["obj"] and settings_win_ref["obj"].winfo_exists():
            settings_win_ref["obj"].focus_set()
            return

        sw = SettingsWindow(
            root,
            initial_sp=controller.pid.setpoint,
            initial_kp=controller.pid.kp,
            initial_ki=controller.pid.ki,
            initial_kd=controller.pid.kd,
            on_set_sp=controller.set_setpoint,
            on_set_pid=controller.set_gains,
            on_enable=controller.enable_control,
            on_autotune_start=lambda params: controller.autotune_start(params)[0],
            on_autotune_stop=controller.autotune_stop,
            on_autotune_apply=lambda: _apply_tuned_and_persist()
        )
        settings_win_ref["obj"] = sw

    def _apply_tuned_and_persist():
        ok, gains = controller.autotune_apply()
        if not ok:
            messagebox.showinfo("Auto-tune", "No tuned gains available yet.")
            return
        if settings_win_ref["obj"] and settings_win_ref["obj"].winfo_exists():
            settings_win_ref["obj"].show_tuned_gains(gains)
        saved, msg = save_tuned_gains_to_config(gains["Kp"], gains["Ki"], gains["Kd"])
        if not saved:
            messagebox.showwarning("Auto-tune", msg)

    # --- NUEVO: control rápido desde la ventana principal ---
    def ui_toggle_enable():
        # La UI refleja 'enabled' en cada update, así que simplemente pedimos al controller lo opuesto:
        controller.enable_control(not controller.enabled)

    def ui_toggle_fan():
        controller.toggle_fan()

    def ui_emergency_stop():
        controller.emergency_stop(sp_zero=True, fan_on_after_stop=False)

    # Bind de callbacks (extendido)
    win.bind_callbacks(
        on_scan=apply_part,
        on_new=ui_add,
        on_edit=ui_update,
        on_delete=ui_delete,
        on_open_settings=open_settings_request,
        on_toggle_fan=ui_toggle_fan,
        on_emergency_stop=ui_emergency_stop,
        on_toggle_enable=ui_toggle_enable,
           # <-- NUEVO
    )

    win.load_parts(storage.list_parts())

    # Botón físico PARO
    try:
        in_cfg = cfg.get("inputs", {}).get("stop_button", {})
        if in_cfg:
            def handle_stop_press():
                controller.emergency_stop(sp_zero=True, fan_on_after_stop=False)
                root.after(0, lambda: messagebox.showwarning("Paro", "Paro de emergencia activado."))
            stop_btn = GPIOButton(
                gpio_chip=in_cfg["gpio_chip"],
                gpio_line=int(in_cfg["gpio_line"]),
                pull=str(in_cfg.get("pull", "up")),
                debounce_ms=int(in_cfg.get("debounce_ms", 60)),
                on_press=handle_stop_press,
            )
    except Exception as e:
        print(f"[WARN] Stop button not available: {e}")

    # Código de barras (si aplica)
    serial_scanner = None
    bc_cfg = cfg.get("barcode", {}).get("serial", {})
    if bc_cfg.get("enabled") and SerialBarcodeScanner is not None:
        def handle_code(code: str):
            root.after(0, apply_part, code)
        try:
            serial_scanner = SerialBarcodeScanner(
                port=bc_cfg["port"],
                baudrate=bc_cfg.get("baudrate", 9600),
                timeout=bc_cfg.get("timeout", 0.1),
                on_code=handle_code
            )
            serial_scanner.start()
        except Exception as e:
            print(f"[WARN] Barcode serial not available: {e}")

    controller.start()

    def on_close():
        try:
            controller.stop(join_timeout=2.0)
        except Exception:
            pass
        try:
            if serial_scanner:
                serial_scanner.stop(join_timeout=2.0)
        except Exception:
            pass
        try:
            if ssr is not None:
                ssr.close()
        except Exception:
            pass
        try:
            if motor is not None:
                motor.close()
        except Exception:
            pass
        try:
            if tc is not None:
                tc.close()
        except Exception:
            pass
        try:
            if fan is not None:
                fan.close()
        except Exception:
            pass
        try:
            if stop_btn is not None:
                stop_btn.close()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()