import RPi.GPIO as GPIO
import time

BUTTON_PIN = 4
SERVO_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
GPIO.setup(SERVO_PIN, GPIO.OUT)

servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0) # Inicia en 0

def set_servo_angle(angle):
    """Mueve el servo al ángulo especificado (0°–180°)."""
    
    duty = 2 + (angle / 18)
    servo.ChangeDutyCycle(duty)


current_angle = -1 

try:
    print("Control de servo con botón (0V / 3.3V)")
    print("→ Botón suelto (LOW) = 0°, Botón presionado (HIGH) = 180°")
    print("Presiona Ctrl+C para salir")

    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            
            if current_angle != 180:
                print("Nivel alto detectado → 180°")
                set_servo_angle(180)
                current_angle = 180
        else:
            
            if current_angle != 0:
                print("Nivel bajo detectado → 0°")
                set_servo_angle(0)
                current_angle = 0
        
        
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nDetenido por el usuario")

finally:
    
    servo.stop()
    GPIO.cleanup()