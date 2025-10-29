import RPi.GPIO as GPIO
import time
import threading
from flask import Flask, jsonify
from datetime import datetime

# CONFIGURACIÓN DE PINES Y LIBRERÍAS

POT_PIN = 4
BMI160_ADDR = 0x69  # Cambiar a 0x68 si el pin SDO del BMI160 está a GND

GPIO.setmode(GPIO.BCM)

# Intentar importar el driver del sensor BMI160
try:
    from BMI160_i2c import Driver
except ImportError:
    print("⚠ No se encontró la librería 'BMI160-i2c'. Instálala con:")
    print("   sudo pip3 install BMI160-i2c smbus2")
    Driver = None

# VARIABLES GLOBALES Y ESTRUCTURA DE DATOS
app = Flask(__name__)
bmi160 = None

datos = {
    # Potenciómetro
    "pot_valor_crudo": 0,
    "pot_porcentaje": "0%",
    "pot_resistencia_aprox": "0Ω",
    # Acelerómetro y giroscopio
    "accel_x": 0.0, "accel_y": 0.0, "accel_z": 0.0,
    "gyro_x": 0.0, "gyro_y": 0.0, "gyro_z": 0.0,
    # Meta
    "ultima_actualizacion": None
}

bloqueo = threading.Lock()
min_val = 0
max_val = 100

# FUNCIONES DEL POTENCIÓMETRO
def leer_potenciometro():
    """Lee el valor del potenciómetro por carga y descarga capacitiva."""
    contador = 0
    GPIO.setup(POT_PIN, GPIO.OUT)
    GPIO.output(POT_PIN, False)
    time.sleep(0.1)
    GPIO.setup(POT_PIN, GPIO.IN)

    while GPIO.input(POT_PIN) == GPIO.LOW:
        contador += 1
        if contador > 100000:  # Evita bloqueos infinitos
            break
    return contador


def calibrar():
    """Calibra los valores mínimo y máximo del potenciómetro."""
    print("Iniciando calibración del potenciómetro (10KΩ)")
    print("➡ Gira completamente a la izquierda (mínimo)...")
    time.sleep(3)
    minimo = leer_potenciometro()

    print("➡ Gira completamente a la derecha (máximo)...")
    time.sleep(3)
    maximo = leer_potenciometro()

    if maximo <= minimo:
        print("⚠ Valores inválidos. Ajustando para evitar división por cero.")
        maximo = minimo + 100

    print(f"Calibración completa → Mínimo={minimo}, Máximo={maximo}")
    return minimo, maximo

# FUNCIÓN PRINCIPAL DE ACTUALIZACIÓN
def bucle_sensores():
    """Hilo que actualiza continuamente los datos del potenciómetro y BMI160."""
    global min_val, max_val

    while True:
        try:
            # 1. Lectura del potenciómetro
            valor = leer_potenciometro()
            if (max_val - min_val) > 0:
                porcentaje = (valor - min_val) / (max_val - min_val) * 100
                porcentaje = max(0, min(100, porcentaje))
            else:
                porcentaje = 0.0

            resistencia = (porcentaje / 100) * 10000  # Potenciómetro de 10kΩ

            # 2. Lectura del BMI160
            datos_bmi = None
            if bmi160:
                try:
                    # Orden del driver: gx, gy, gz, ax, ay, az
                    datos_bmi = bmi160.getMotion6()
                except Exception as e:
                    print(f"⚠ Error al leer BMI160: {e}")
                    datos_bmi = None

            # 3. Actualización del diccionario global
            with bloqueo:
                datos.update({
                    "pot_valor_crudo": valor,
                    "pot_porcentaje": f"{porcentaje:5.1f}%",
                    "pot_resistencia_aprox": f"~{resistencia:4.0f}Ω",
                    "ultima_actualizacion": datetime.now().isoformat()
                })

                if datos_bmi:
                    datos["gyro_x"], datos["gyro_y"], datos["gyro_z"], datos["accel_x"], datos["accel_y"], datos["accel_z"] = datos_bmi

            # 4. Log simplificado
            estado_bmi = "OK" if datos_bmi else "ERR"
            print(f"Pot: {porcentaje:5.1f}% ({valor:5d}) | BMI[{estado_bmi}] Ax={datos['accel_x']:.2f}, Gy={datos['gyro_x']:.2f}")
            time.sleep(0.3)

        except Exception as e:
            print(f"Error general en bucle_sensores(): {e}")
            time.sleep(2)

# ENDPOINTS DE LA API FLASK
@app.route('/')
def inicio():
    """Endpoint raíz con info general."""
    return jsonify({
        "mensaje": "API de Doble Sensor (Potenciómetro + BMI160)",
        "endpoints": ["/api/sensor", "/api/estado"]
    })


@app.route('/api/sensor')
def obtener_datos():
    """Devuelve los datos actuales de ambos sensores."""
    with bloqueo:
        return jsonify(datos.copy())


@app.route('/api/estado')
def obtener_estado():
    """Devuelve el estado general del sistema."""
    return jsonify({
        "estado": "en ejecución",
        "timestamp": datetime.now().isoformat()
    })

# CONFIGURACIÓN INICIAL Y SERVIDOR
def iniciar():
    """Inicializa sensores, calibración y servidor web."""
    global min_val, max_val, bmi160

    # 1. Calibrar potenciómetro
    min_val, max_val = calibrar()

    # 2. Inicializar BMI160 si está disponible
    if Driver:
        try:
            bmi160 = Driver(BMI160_ADDR)
            print(f"Sensor BMI160 inicializado en dirección I2C: {hex(BMI160_ADDR)}")
        except Exception as e:
            print(f"⚠ No se pudo inicializar el BMI160: {e}")
            bmi160 = None
    else:
        print("⚠ El módulo BMI160-i2c no está disponible. Se usará solo el potenciómetro.")

    # 3. Iniciar hilo de lectura
    print("Iniciando hilo de actualización de sensores...")
    hilo = threading.Thread(target=bucle_sensores, daemon=True)
    hilo.start()

    # 4. Iniciar servidor Flask
    print("Servidor disponible en: http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# PUNTO DE ENTRADA
if __name__ == "__main__":
    try:
        iniciar()
    except KeyboardInterrupt:
        print("\n Interrupción detectada. Cerrando servidor...")
    finally:
        GPIO.cleanup()
        print("GPIO limpiado correctamente. Adiós.")