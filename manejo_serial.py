import serial
import time
import struct
import queue

def readserial(comport, baudrate, data_queue, comienzo, t_ensayo=60, RPM_ensayo=800):
    try:
        ser = serial.Serial(comport, baudrate, timeout=0.1)
        ser.flushInput()
        ser.flushOutput()
    except Exception as e:
        print(f"Error al abrir el puerto serie {comport}: {e}")
        comienzo[0] = False
        return

    # Formato de la trama binaria (Little-endian '<')
    # L = uint32 (4 bytes) -> Tiempo
    # f = float (4 bytes)  -> Temp Amb
    # f = float (4 bytes)  -> Temp Obj
    # L = uint32 (4 bytes) -> Vueltas
    # l = int32 (4 bytes)  -> Carga
    packet_format = '<LffLl'
    
    buffer = bytearray()
    ensayo_iniciado = False

    while comienzo[0]:
        # 1. Leer todos los bytes disponibles en el puerto
        if ser.in_waiting > 0:
            buffer.extend(ser.read(ser.in_waiting))

        # 2. Lógica de inicio (Esperar a que el Arduino diga que está listo)
        if not ensayo_iniciado:
            if b'Iniciando' in buffer:
                comando = f'TESTSTART-{RPM_ensayo:06d}-{t_ensayo:06d}\n'
                ser.write(comando.encode('utf-8'))
                print('Comando de inicio enviado:', comando.strip())
                ensayo_iniciado = True
                buffer.clear()  # Limpiamos el buffer de textos viejos
        
        # 3. Lógica de adquisición de datos (Binario)
        else:
            # Comprobar si el Arduino terminó el ensayo
            if b'TESTEND' in buffer:
                print("Lectura detenida por el hardware (TESTEND)")
                break

            # Buscar paquetes mientras haya suficientes bytes en el buffer (23 bytes totales)
            while len(buffer) >= 23:
                # Buscar el primer byte de la cabecera (0xAA)
                idx = buffer.find(b'\xAA')
                
                if idx == -1:
                    # Si no hay 0xAA en todo el buffer, es basura. Borrar todo.
                    buffer.clear()
                    break
                
                if idx > 0:
                    # Si el 0xAA no está al principio, descartamos lo que haya antes
                    del buffer[:idx]
                    continue 
                
                # Ahora buffer[0] es 0xAA. Comprobamos el segundo byte (0xBB)
                if buffer[1] != 0xBB:
                    # Falso positivo (un byte random era 0xAA). Lo borramos y seguimos buscando
                    del buffer[:1]
                    continue
                
                # Tenemos la cabecera completa en las posiciones 0 y 1.
                # Verificamos si ya llegaron los 23 bytes de este paquete
                if len(buffer) >= 23:
                    payload = buffer[2:22]      # Los 20 bytes de datos
                    rcv_checksum = buffer[22]   # El byte de checksum
                    
                    # Calcular el checksum sumando los bytes del payload (truncado a 8 bits con & 0xFF)
                    calc_checksum = sum(payload) & 0xFF
                    
                    if calc_checksum == rcv_checksum:
                        # ¡PAQUETE VÁLIDO! Desempaquetamos los bytes a variables de Python
                        # datos = (tiempo, temp_amb, temp_obj, vueltas, carga)
                        datos = struct.unpack(packet_format, payload)
                        
                        # Metemos los datos en la Cola segura para que la GUI los lea
                        data_queue.put(datos)
                    else:
                        # El ruido rompió el paquete. Se descarta en silencio.
                        # print("Checksum fallido, paquete descartado.")
                        pass
                    
                    # Eliminamos los 23 bytes ya procesados del buffer
                    del buffer[:23]
                else:
                    # Encontramos la cabecera pero faltan llegar bytes del final.
                    # Salimos del while para esperar a que lleguen en la próxima vuelta.
                    break

        # Pequeña pausa para no poner el procesador de la PC al 100%
        time.sleep(0.001)

    # --- FIN DEL HILO ---
    print('Cerrando puerto serie y deteniendo ensayo...')
    if ser.is_open:
        ser.write(b'TESTSTOP\n')
        time.sleep(0.1)
        ser.close()