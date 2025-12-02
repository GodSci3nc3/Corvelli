import serial
import time

# Configuración del puerto serial
PUERTO = '/dev/ttyUSB0'
BAUDRATE = 9600
TIMEOUT = 1

print("Conectando al switch via serial...")

try:
    # Abrir conexión serial
    ser = serial.Serial(
        port=PUERTO,
        baudrate=BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT
    )
    
    print(f"Conectado en {PUERTO}")
    
    # Esperar un momento
    time.sleep(2)
    
    # Enviar Enter para activar el prompt
    ser.write(b'\n')
    time.sleep(1)
    
    # Leer lo que haya en buffer
    if ser.in_waiting:
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        print("Respuesta inicial:")
        print(response)
    
    # Enviar comando show version
    print("\nEnviando: show version")
    ser.write(b'show version\n')
    time.sleep(3)
    
    # Leer respuesta
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print("\nRespuesta del switch:")
    print(response)
    
    # Cerrar conexión
    ser.close()
    print("\nConexion cerrada")
    
except serial.SerialException as e:
    print(f"Error al conectar: {e}")
    print("\nVerifica:")
    print("1. Cable conectado correctamente")
    print("2. Switch encendido")
    print("3. Permisos: sudo chmod 666 /dev/ttyUSB0")
except Exception as e:
    print(f"Error inesperado: {e}")