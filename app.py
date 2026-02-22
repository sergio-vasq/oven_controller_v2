import sys
import yaml
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from data.storage import Storage
from services.controller import ControllerV2
from ui_ctk.main_window_ctk import MainWindow
from ui_ctk.settings_window_ctk import SettingsWindow

from devices.thermocouple_max6675 import MAX6675
from devices.ssr_timeproportion import SSRTimeProportion
from devices.dc_motor_pwm import DCMotorPWM

try:
    from barcode.scanner_serial import SerialBarcodeScanner
except Exception:
    SerialBarcodeScanner = None

CONFIG_PATH = Path("config.yaml")


def save_tuned_gains_to_config(kp: float, ki: float, kd: float):
    """Persist tuned PID gains into config.yaml under the `pid` section."""
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
    # Default minimal config if file is missing
    return {
        "pid": {
            "kp": 10.0,
            "ki": 1.0,
            "kd": 0.0,
            "sample_seconds": 0.5,
            "output_limits": [0.0, 100.0],
        },
        "ui": {
            "appearance": "Dark",  # "Dark" | "Light" | "System"
            "theme": "blue",       # "blue" | "green" | "dark-blue"
            "geometry": "1100x720",
        }
    }


def main():
    cfg = _load_config()
    storage = Storage()

    # --- Devices (all optional; guarded by try/except) ---
    tc = None
    ssr = None
    motor = None
    try:
        th_cfg = cfg.get("thermocouple", {})
        if th_cfg:
            tc = MAX6675(
                spi_device=th_cfg["spi_device"],
                mode=int(th_cfg.get("spi_mode", 0)),
                max_hz=int(th_cfg.get("spi_max_hz", 4_000_000)),
                samples_avg=max(1, int(th_cfg.get("samples_avg", 1)))
            )
    except Exception as e:
        print(f"[WARN] MAX6675 not available: {e}")

    try:
        ssr_cfg = cfg.get("ssr", {})
        if ssr_cfg:
            ssr = SSRTimeProportion(
                gpio_chip=ssr_cfg["gpio_chip"],
                gpio_line=int(ssr_cfg["gpio_line"]),
                active_high=bool(ssr_cfg.get("active_high", True)),
                window_s=float(ssr_cfg.get("window_seconds", 1.0))
            )
    except Exception as e:
        print(f"[WARN] SSR GPIO not available: {e}")

    try:
        motor_cfg = cfg.get("motor", {})
        if motor_cfg:
            motor = DCMotorPWM(motor_cfg)  # software/hardware via config
    except Exception as e:
        print(f"[WARN] Motor PWM not available: {e}")

    # --- Root window (CustomTkinter) ---
    ui_cfg = cfg.get("ui", {})
    ctk.set_appearance_mode(ui_cfg.get("appearance", "Dark"))
    ctk.set_default_color_theme(ui_cfg.get("theme", "blue"))

    root = ctk.CTk()
    root.title("Oven Controller CSC")
    geometry = ui_cfg.get("geometry", "1100x720")
    try:
        root.geometry(geometry)
    except Exception:
        root.geometry("1100x720")

    # --- Main window (operator UI) ---
    win = MainWindow(root)
    appearance = ui_cfg.get("appearance", "Dark")
    win.apply_theme(appearance)

    # --- Controller & dispatcher ---
    pid_cfg = cfg.get("pid", {})
    saf_cfg = cfg.get("safety", {})
    at_cfg = cfg.get("autotune", {})

    # single-instance ref for settings window
    settings_win_ref = {"obj": None}

    # small latch to not spam AT-DONE prints (optional)
    _done_latch = {"printed": False}

    def _ui_update_dispatch(data: dict):
        """
        Dispatch controller state to MainWindow and, if open, to SettingsWindow.
        Also logs AT-DONE (if present) once.
        """
        # Update main window (plot, status)
        win.handle_update(data)

        # Update settings window (autotune pane) if open
        sw = settings_win_ref.get("obj")
        if sw is not None and sw.winfo_exists():
            at_status = data.get("autotune", {})
            try:
                sw.update_autotune(at_status)
            except Exception as e:
                print("[WARN] SettingsWindow.update_autotune failed:", e)

        # Optional: console log when autotune reports DONE (once)
        at = data.get("autotune", {}) or {}
        if at.get("status") == "done" and not _done_latch["printed"]:
            _done_latch["printed"] = True
            try:
                print("[AT-DONE]",
                      f"Tu={at.get('Tu')}",
                      f"Ku={at.get('Ku')}",
                      f"Kp={at.get('Kp')}",
                      f"Ki={at.get('Ki')}",
                      f"Kd={at.get('Kd')}")
            except Exception:
                pass

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
        # IMPORTANT: route updates through the dispatcher, not directly to MainWindow
        on_update=lambda data: root.after(0, _ui_update_dispatch, data)
    )  # Se integra con tu ControllerV2 existente. [1](https://autozone1com-my.sharepoint.com/personal/sergio_vasquez_autozone_com/Documents/Microsoft%20Copilot%20Chat%20Files/autotune.py)

    # --- Callbacks used by main ---
    def apply_part(code: str):
        ok, part = controller.apply_part(code)
        if not ok:
            messagebox.showwarning("Not found", f"Part code '{code}' not found.")
        else:
            win.load_setpoint(part["temp_setpoint"])  # reflect SP on status area
            win.load_parts(storage.list_parts())      # refresh list

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

    # Settings window creation (single-instance behavior)
    def open_settings():
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
            # start returns (ok, msg); we only need bool to drive UI state
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

        # console confirmation
        try:
            print("[AT-APPLY]", f"Kp={gains['Kp']:.4f} Ki={gains['Ki']:.4f} Kd={gains['Kd']:.4f}")
        except Exception:
            pass

    # Bind and load data
    win.bind_callbacks(
        on_scan=apply_part,
        on_new=ui_add,
        on_edit=ui_update,
        on_delete=ui_delete,
        on_open_settings=open_settings,
    )
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

    # Start controller after UI is ready
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
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()