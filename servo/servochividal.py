import RPi.GPIO as GPIO
import time

POT_PIN = 4
SERVO_PIN = 17
FREQ_HZ = 50
MIN_DUTY = 2.5
MAX_DUTY = 12.5

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def read_potentiometer():
    count = 0
    GPIO.setup(POT_PIN, GPIO.OUT)
    GPIO.output(POT_PIN, False)
    time.sleep(0.05)
    GPIO.setup(POT_PIN, GPIO.IN)
    while GPIO.input(POT_PIN) == GPIO.LOW:
        count += 1
        if count > 50000:
            break
    return count

def calibrate():
    print("Calibrando para potenciómetro 5K...")
    print("Gira completamente a la izquierda (mínimo)")
    time.sleep(3)
    min_val = read_potentiometer()
    print("Gira completamente a la derecha (máximo)")
    time.sleep(3)
    max_val = read_potentiometer()
    print(f"Calibración: Mínimo={min_val}, Máximo={max_val}")
    return min_val, max_val

def angle_to_duty(angle):
    angle = max(0, min(180, angle))
    return MIN_DUTY + (MAX_DUTY - MIN_DUTY) * (angle / 180.0)

def goto_angle(pwm, angle):
    pwm.ChangeDutyCycle(angle_to_duty(angle))

try:
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, FREQ_HZ)
    pwm.start(angle_to_duty(0))
    time.sleep(0.5)

    min_value, max_value = calibrate()

    estado = None
    print("Leyendo potenciómetro de 5K... (Ctrl+C para detener)")
    while True:
        value = read_potentiometer()

        if max_value - min_value > 0:
            normalized = (value - min_value) / (max_value - min_value)
            normalized = max(0.0, min(1.0, normalized))
        else:
            normalized = 0.5

        v_est = 3.3 * normalized
        resistencia_aprox = (value / max_value) * 5000 if max_value else 0

        if v_est >= 3.3 and estado != "HIGH":
            goto_angle(pwm, 180)
            estado = "HIGH"
            print(f"Valor crudo: {value:5d} -> {normalized*100:5.1f}% -> ~{int(resistencia_aprox):4d}Ω -> V≈{v_est:0.2f} -> 1 -> Servo 180°")
        elif v_est < 0.5 and estado != "LOW":
            goto_angle(pwm, 0)
            estado = "LOW"
            print(f"Valor crudo: {value:5d} -> {normalized*100:5.1f}% -> ~{int(resistencia_aprox):4d}Ω -> V≈{v_est:0.2f} -> 0 -> Servo 0°")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nDetenido por el usuario")
finally:
    try:
        pwm.stop()
    except:
        pass
    GPIO.cleanup()