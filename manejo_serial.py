import serial
import time
import struct
import csv

def readserial(comport, baudrate, data_queue, comienzo, csv_path, t_ensayo, RPM_ensayo, factor_k, offset):
    try:
        ser = serial.Serial(comport, baudrate, timeout=0.1)
        ser.flushInput()
        csv_file = open(csv_path, 'w', newline='')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["Tiempo(ms)", "TempAmb(C)", "TempObj(C)", "Vueltas", "Carga(kg)"])
    except:
        comienzo[0] = False
        return

    packet_format = '<LffLl'
    buffer = bytearray()
    ensayo_iniciado = False

    while comienzo[0]:
        if ser.in_waiting > 0:
            buffer.extend(ser.read(ser.in_waiting))

        if not ensayo_iniciado:
            if b'Iniciando' in buffer:
                ser.write(f'TESTSTART-{RPM_ensayo:06d}-{t_ensayo:06d}\n'.encode())
                ensayo_iniciado = True
                buffer.clear() 
        else:
            if b'TESTEND' in buffer: break
            while len(buffer) >= 23:
                idx = buffer.find(b'\xAA')
                if idx == -1: break
                if idx > 0: del buffer[:idx]; continue
                if buffer[1] != 0xBB: del buffer[:1]; continue
                
                if len(buffer) >= 23:
                    payload = buffer[2:22]
                    if (sum(payload) & 0xFF) == buffer[22]:
                        d = list(struct.unpack(packet_format, payload))
                        # CALIBRACIÓN: Carga(kg) = (Raw - Offset) * K
                        d[4] = (d[4] - offset) * factor_k
                        csv_writer.writerow(d)
                        data_queue.put(tuple(d))
                    del buffer[:23]
                else: break
        time.sleep(0.001)

    ser.write(b'TESTSTOP\n')
    ser.close()
    csv_file.close()