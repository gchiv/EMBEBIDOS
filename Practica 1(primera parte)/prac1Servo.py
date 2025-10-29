import RPi.GPIO as GPIO
import time
import threading
import logging
import signal
import sys
from flask import Flask, jsonify
from datetime import datetime

# CONFIGURACIÓN INICIAL DEL SISTEMA
PIN_POT = 4
GPIO.setmode(GPIO.BCM)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

app = Flask(__name__)

# VARIABLES GLOBALES

datos_sensor = {
    "valor_crudo": 0,
    "porcentaje": "0%",
    "resistencia_aprox": "0Ω",
    "ultima_actualizacion": None
}
lock_datos = threading.Lock()

min_valor = 0
max_valor = 100
activo = True  # Control del hilo principal

# FUNCIONES DEL SENSOR

def leer_potenciometro():
    """Lee el valor del potenciómetro mediante el método de carga y descarga."""
    contador = 0
    GPIO.setup(PIN_POT, GPIO.OUT)
    GPIO.output(PIN_POT, False)
    time.sleep(0.1)

    GPIO.setup(PIN_POT, GPIO.IN)

    while GPIO.input(PIN_POT) == GPIO.LOW:
        contador += 1
        if contador > 100000:  # Timeout de seguridad
            break
    return contador


def calibrar():
    """Realiza la calibración inicial para definir los valores mínimo y máximo."""
    logging.info("🛠 Iniciando calibración del potenciómetro (10K)...")

    logging.info("Gira completamente a la izquierda (mínimo)...")
    time.sleep(3)
    minimo = leer_potenciometro()

    logging.info("Ahora gira completamente a la derecha (máximo)...")
    time.sleep(3)
    maximo = leer_potenciometro()

    if maximo <= minimo:
        logging.warning("⚠ Valores de calibración inválidos. Ajustando automáticamente...")
        maximo = minimo + 100

    logging.info(f"Calibración completada → Mínimo={minimo}, Máximo={maximo}")
    return minimo, maximo


def actualizar_sensor():
    """Hilo en segundo plano que actualiza los datos del sensor cada 300 ms."""
    global activo
    while activo:
        try:
            valor = leer_potenciometro()
            if (max_valor - min_valor) > 0:
                porcentaje = (valor - min_valor) / (max_valor - min_valor) * 100
                porcentaje = max(0, min(100, porcentaje))
            else:
                porcentaje = 0

            resistencia = (porcentaje / 100) * 10000  # Potenciómetro de 10KΩ

            with lock_datos:
                datos_sensor.update({
                    "valor_crudo": valor,
                    "porcentaje": f"{porcentaje:5.1f}%",
                    "resistencia_aprox": f"~{resistencia:4.0f}Ω",
                    "ultima_actualizacion": datetime.now().isoformat()
                })

            logging.info(f"Lectura → Crudo={valor:5d} | {porcentaje:5.1f}% | ~{resistencia:5.0f}Ω")
            time.sleep(0.3)

        except Exception as e:
            logging.error(f"Error en actualización del sensor: {e}")
            time.sleep(2)

# ENDPOINTS DE LA API

@app.route('/')
def inicio():
    """Ruta raíz: muestra información general."""
    return jsonify({
        "mensaje": "API del Sensor de Potenciómetro - Raspberry Pi",
        "endpoints": ["/api/sensor", "/api/estado", "/api/calibrar"]
    })


@app.route('/api/sensor')
def obtener_datos():
    """Devuelve los datos actuales del sensor en formato JSON."""
    with lock_datos:
        return jsonify(datos_sensor.copy())


@app.route('/api/estado')
def estado_sistema():
    """Devuelve el estado general del sistema."""
    return jsonify({
        "estado": "sistema operativo y monitoreando",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/calibrar')
def recalibrar():
    """Permite recalibrar el sensor desde la API (sin reiniciar el sistema)."""
    global min_valor, max_valor
    min_valor, max_valor = calibrar()
    return jsonify({
        "mensaje": "Recalibración completada",
        "nuevo_minimo": min_valor,
        "nuevo_maximo": max_valor
    })

# CONTROL Y FINALIZACIÓN SEGURA

def detener_programa(sig, frame):
    """Maneja Ctrl+C y cierra el programa de forma segura."""
    global activo
    logging.info("\n Interrupción detectada. Cerrando servidor y limpiando GPIO...")
    activo = False
    time.sleep(1)
    GPIO.cleanup()
    logging.info("GPIO limpiado correctamente. Programa finalizado.")
    sys.exit(0)


def iniciar():
    """Configuración inicial del sistema y ejecución del servidor."""
    global min_valor, max_valor
    signal.signal(signal.SIGINT, detener_programa)

    min_valor, max_valor = calibrar()

    logging.info("Iniciando hilo de actualización del sensor...")
    hilo_sensor = threading.Thread(target=actualizar_sensor, daemon=True)
    hilo_sensor.start()

    logging.info("Servidor Flask ejecutándose en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

# PUNTO DE ENTRADA
if __name__ == "__main__":
    iniciar()