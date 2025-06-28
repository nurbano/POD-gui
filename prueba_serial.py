import serial
import time
import pandas as pd

def readserial(comport, baudrate, timestamp=False, TIMESTAMP=[], VALUES=[], comienzo=[], columns_name=[], t_ensayo=60, RPM_ensayo=800):

    ser = serial.Serial(comport, baudrate, timeout=0.1)         # 1/timeout is the frequency at which the port is read
    ser.flushInput()                                            # Flush the input buffer to remove any old data
    ser.flushOutput()                                           # Flush the output buffer to remove any old data

    while comienzo[0]:

        data = ser.readline().decode().strip()
        if data and timestamp:
            timestamp = time.strftime('%H:%M:%S')
          
        if "tiempoMs," in data:
            columns_name = list( map(str, data.split(',')))
            columns_name.insert(0, "timestamp")
            
        elif "," in data:
            try:
                values = list(map(float, data.split(',')))
            except ValueError:
                print(f"Error converting data to float: {data}")
                values= [0,0,0,0,0]
                continue
            timestamp = time.strftime('%H:%M:%S')
            values.insert(0, timestamp)
            VALUES.append(values)
           
        elif data:
            print(data)
        if data =='Iniciando....':
            ser.write(bytes(f'TESTSTART-{RPM_ensayo:06d}-{t_ensayo:06d}', 'utf-8'))
            #ser.write(bytes('TESTSTART-000800-000900', 'utf-8'))
            print('Enviando comando de lectura...')
        if data == 'TESTEND':
            print('Lectura detenida')
            ser.close()  # Close the serial port when done
            break
    if comienzo[0]== False:
        print('Enviando comando de parada...')
        ser.write(bytes('TESTEND', 'utf-8'))  # Send a command to stop the test
        ser.close()  # Close the serial port when done
    exit(0)
