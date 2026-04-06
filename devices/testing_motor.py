from periphery import PWM
import time

# Ajusta estos valores si usas otro chip/canal
PWM_CHIP = 0
PWM_CHANNEL = 0

print("Opening PWM...")
pwm = PWM(PWM_CHIP, PWM_CHANNEL)

# MUY IMPORTANTE: setear frecuencia antes de enable
print("Configuring PWM...")
pwm.frequency = 1000.0     # 1 kHz
pwm.duty_cycle = 0.5      # 50%

print("Enabling PWM...")
pwm.enable()

print("PWM running for 10 seconds...")
time.sleep(10)

print("Stopping PWM...")
pwm.duty_cycle = 0.0
pwm.disable()
pwm.close()

print("Done.")
