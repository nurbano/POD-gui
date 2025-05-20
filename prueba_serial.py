import serial
import time
import pandas as pd

def readserial(comport, baudrate, timestamp=False, TIMESTAMP=[], VALUES=[], comienzo=False, columns_name=[]):

    ser = serial.Serial(comport, baudrate, timeout=0.1)         # 1/timeout is the frequency at which the port is read
    ser.flushInput()                                            # Flush the input buffer to remove any old data
    ser.flushOutput()                                           # Flush the output buffer to remove any old data
    #VALUES=[]
    #ser.write(b'TESTSTART-000800-000015\n')  # Send a string to the serial port
    while True:

        data = ser.readline().decode().strip()

        if data and timestamp:
            timestamp = time.strftime('%H:%M:%S')
            
            #print(f'{timestamp} > {data}')
        
        if "tiempoMs," in data:
            columns_name = list( map(str, data.split(',')))
            columns_name.insert(0, "timestamp")
            
        elif "," in data:
            #comienzo = True
            values = list(map(float, data.split(',')))
            timestamp = time.strftime('%H:%M:%S')
            values.insert(0, timestamp)
            # Append the values to the list
            VALUES.append(values)
            
        elif data:
            print(data)
        if data =='Iniciando....':
            ser.write(bytes('TESTSTART-000800-000005', 'utf-8'))
            print('Enviando comando de lectura...')
        if data == 'TESTEND':
            print('Lectura detenida')
            # df = pd.DataFrame(VALUES, columns=columns_name)
            # print(df.head())
            # df.to_csv('data.csv', index=False)
            # print('Guardando datos en data.csv')
            break
 
def begin_test(ser):
    print('Enviando comando de lectura...')
    ser.write(bytes('TESTSTART-000800-000005', 'utf-8'))  # Send a string to the serial port
    
    #time.sleep(1)  # Wait for 1 second before reading again

if __name__ == '__main__':

    readserial('COM4', 115200, True)  
   