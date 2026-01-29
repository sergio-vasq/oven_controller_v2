import sys
import yaml
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from data.storage import Storage
from services.controller_v2 import ControllerV2
from ui_tk.main_window import MainWindow
from ui_tk.settings_window import SettingsWindow

# Hardware drivers
from devices.thermocouple_max6675 import MAX6675
from devices.ssr_timeproportion import SSRTimeProportion
from devices.dc_motor_pwm import DCMotorPWM

# Optional serial barcode
try:
    from barcode.scanner_serial import SerialBarcodeScanner
except Exception:
    SerialBarcodeScanner = None

CONFIG_PATH = Path("config.yaml")

def save_tuned_gains_to_config(kp: float, ki: float, kd: float):
    try:
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

def main():
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    storage = Storage()

    # Build devices (tolerant on Windows/dev)
    tc = None
    ssr = None
    motor = None
    try:
        tc = MAX6675(
            spi_device=cfg["thermocouple"]["spi_device"],
            mode=int(cfg["thermocouple"].get("spi_mode", 0)),
            max_hz=int(cfg["thermocouple"].get("spi_max_hz", 4000000)),
            samples_avg=max(1, int(cfg["thermocouple"].get("samples_avg", 1)))
        )
    except Exception as e:
        print(f"[WARN] MAX6675 not available: {e}")
    try:
        ssr = SSRTimeProportion(
            gpio_chip=cfg["ssr"]["gpio_chip"],
            gpio_line=int(cfg["ssr"]["gpio_line"]),
            active_high=bool(cfg["ssr"].get("active_high", True)),
            window_s=float(cfg["ssr"].get("window_seconds", 1.0))
        )
    except Exception as e:
        print(f"[WARN] SSR GPIO not available: {e}")
    try:
        motor = DCMotorPWM(cfg["motor"])  # software/hardware via config
    except Exception as e:
        print(f"[WARN] Motor PWM not available: {e}")

    root = tk.Tk()

    # Build controller
    pid_cfg = cfg["pid"]
    saf_cfg = cfg.get("safety", {})
    at_cfg  = cfg.get("autotune", {})

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
        on_update=lambda data: root.after(0, win.update_status, data)
    )
    controller.start()

    # Main window (operator UI only)
    win = MainWindow(root)
    root.iconbitmap(default="oven.ico")

    # --- Callbacks used by main ---
    def apply_part(code: str):
        ok, part = controller.apply_part(code)
        if not ok:
            messagebox.showwarning("Not found", f"Part code '{code}' not found.")
        else:
            win.load_setpoint(part["temp_setpoint"])  # reflect SP on status area
            win.load_parts(storage.list_parts())       # refresh list (optional)

    def ui_add(payload):
        try:
            storage.add_part(payload["code"], payload["temp"], payload["speed"], payload.get("notes",""))
            win.load_parts(storage.list_parts())
            win.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add: {e}")

    def ui_update(payload):
        try:
            storage.update_part(payload["code"], payload["temp"], payload["speed"], payload.get("notes",""))
            win.load_parts(storage.list_parts())
            win.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")

    def ui_delete(code):
        try:
            storage.delete_part(code)
            win.load_parts(storage.list_parts())
            win.clear_form()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    # Settings window creation
    settings_win_ref = {"obj": None}

    def open_settings():
        if settings_win_ref["obj"] and settings_win_ref["obj"].winfo_exists():
            settings_win_ref["obj"].focus_set()
            return
        sw = SettingsWindow(root,
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
        # show in settings window if still open
        if settings_win_ref["obj"] and settings_win_ref["obj"].winfo_exists():
            settings_win_ref["obj"].show_tuned_gains(gains)
        # persist to YAML
        saved, msg = save_tuned_gains_to_config(gains["Kp"], gains["Ki"], gains["Kd"])
        if not saved:
            messagebox.showwarning("Auto-tune", msg)

    # Bind and load data
    win.bind_callbacks(on_scan=apply_part, on_add=ui_add, on_update=ui_update, on_delete=ui_delete, on_open_settings=open_settings)
    win.load_parts(storage.list_parts())

    # Optional serial barcode
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
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
