# Oven Controller V2 — Technician Settings Window

This build removes the manual **Motor speed** slider from the main UI and moves **Control** (SP & PID gains) and **Auto‑tune** to a separate **Settings** window. The main UI is now operator‑focused: Status, Scan/Enter Part Code, Parts Library and CRUD.

- Technicians open **Settings** to run auto‑tune and/or adjust Kp/Ki/Kd.
- When clicking **Apply tuned gains**, Kp/Ki/Kd are **saved into `config.yaml`** and will load on next run.
- Selecting a part applies its **setpoint** and **motor speed** automatically; operators cannot change motor speed manually.

## Install (Debian/Radxa)
```
sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv
python3 -m venv .venv && . .venv/bin/activate
pip3 install -r requirements.txt
python3 app_v2.py
```
Enable SPI (`/dev/spidevX.Y`) and ensure permissions for `/dev/gpiochip*`.
