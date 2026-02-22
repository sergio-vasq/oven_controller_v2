## Install (Debian/Radxa)
```
sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv
python3 -m venv .venv && . .venv/bin/activate
pip3 install -r requirements.txt
python3 app.py
```
Enable SPI (`/dev/spidevX.Y`) and ensure permissions for `/dev/gpiochip*`.

# PIN Configuration
MAX6675
- GND PIN_9  (GND)
- VCC PIN_1  (+3.3V)
- SCK PIN_23 (SPI0_CLK)
- CS  PIN_26 (SPI0_CSN1)
- S0  PIN_21 (SPI0_MISO)

SSR (Oven)
- GND PIN_6  (GND)
- VDC PIN_35 (VCC)

BTS7960 Driver (PWM)
- GND PIN_34 (GND)
- VDC PIN_2 (VCC +5V)
- L_EN PIN_15
- R_EN PIN_16
- LPWM PIN_39 (GND)
- RPWM PIN_32 (PWM0_M0)

