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
- GND   | PIN_9  (GND)       | Brown
- VCC   | PIN_1  (+3.3V)     | Red/Purple
- SCK   | PIN_23 (SPI0_CLK)  | Orange
- CS    | PIN_26 (SPI0_CSN1) | Yellow
- S0    | PIN_21 (SPI0_MISO) | Green

SSR (Oven)
- GND   | PIN_6  (GND)       | Black
- VDC   | PIN_35 (VCC)       | Red

BTS7960 Driver (PWM)
- GND   | PIN_34 (GND)       | Black
- VDC   | PIN_2 (VCC +5V)    | Red
- L_EN  | PIN_15             | Brown
- R_EN  | PIN_16             | Orange
- LPWM  | PIN_39 (GND)       | Yellow
- RPWM  | PIN_32 (PWM0_M0)   | Green

Stop Button
- VCC   | PIN_17 (+3.3V)     | Brown
- Sign  | PIN_3              | White

Vent
- GND   | PIN_14 (GND)       | Purple
- Sign  | PIN_7              | Gray