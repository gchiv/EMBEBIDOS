import RPi.GPIO as GPIO
import time


SERVO_PIN = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0) 

def set_servo_angle(angle):

    duty = 2.5 + (angle + 90) / 180 * 10
    
    pwm.ChangeDutyCycle(duty)
    
    time.sleep(0.5)
   
    pwm.ChangeDutyCycle(0)


try:
    print("Iniciando secuencia del servomotor. Presiona CTRL+C para detener.")
    while True:
        print("Moviendo a 90 grados...")
        set_servo_angle(90)
        time.sleep(3)

        print("Moviendo a -90 grados...")
        set_servo_angle(-90)
        time.sleep(3)

except KeyboardInterrupt:
    print("Programa detenido por el usuario.")

finally:
    pwm.stop()          
    GPIO.cleanup()      
    print("GPIO limpiado y programa finalizado.")