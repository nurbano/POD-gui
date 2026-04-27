import serial
import time
import struct
import queue
import csv

def readserial(comport, baudrate, data_queue, comienzo, csv_path, t_ensayo=60, RPM_ensayo=800):
    try:
        ser = serial.Serial(comport, baudrate, timeout=0.1)
        ser.flushInput()
        ser.flushOutput()
    except Exception as e:
        print(f"Error al abrir el puerto serie {comport}: {e}")
        comienzo[0] = False
        return

    packet_format = '<LffLl'
    buffer = bytearray()
    ensayo_iniciado = False
    
    # Abrir archivo CSV desde este hilo (I/O asíncrono respecto a la UI)
    try:
        csv_file = open(csv_path, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["Tiempo(ms)", "TempAmb(C)", "TempObj(C)", "Vueltas", "Carga"])
    except Exception as e:
        print("Error abriendo archivo CSV:", e)
        comienzo[0] = False
        return

    while comienzo[0]:
        if ser.in_waiting > 0:
            buffer.extend(ser.read(ser.in_waiting))

        if not ensayo_iniciado:
            if b'Iniciando' in buffer:
                comando = f'TESTSTART-{RPM_ensayo:06d}-{t_ensayo:06d}\n'
                ser.write(comando.encode('utf-8'))
                print('Comando de inicio enviado:', comando.strip())
                ensayo_iniciado = True
                buffer.clear() 
        else:
            if b'TESTEND' in buffer:
                print("Lectura detenida por el hardware (TESTEND)")
                break

            while len(buffer) >= 23:
                idx = buffer.find(b'\xAA')
                
                if idx == -1:
                    buffer.clear()
                    break
                if idx > 0:
                    del buffer[:idx]
                    continue 
                if buffer[1] != 0xBB:
                    del buffer[:1]
                    continue
                
                if len(buffer) >= 23:
                    payload = buffer[2:22]
                    rcv_checksum = buffer[22]
                    calc_checksum = sum(payload) & 0xFF
                    
                    if calc_checksum == rcv_checksum:
                        datos = struct.unpack(packet_format, payload)
                        
                        # 1. Guardar en disco INMEDIATAMENTE desde el hilo de adquisición
                        csv_writer.writerow(datos)
                        
                        # 2. Mandar a la UI para graficar
                        data_queue.put(datos)
                    
                    del buffer[:23]
                else:
                    break

        time.sleep(0.001)

    print('Cerrando puerto serie y deteniendo ensayo...')
    if ser.is_open:
        ser.write(b'TESTSTOP\n')
        time.sleep(0.1)
        ser.close()
        
    # Asegurarnos de cerrar el archivo temporal
    csv_file.close()