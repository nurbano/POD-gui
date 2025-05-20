import logging
import threading
import time
from prueba_serial import readserial
from queue import Queue
import pandas as pd

def thread_function(name):
    logging.info("Thread %s: starting", name)
    time.sleep(2)
    logging.info("Thread %s: finishing", name)
TIMESTAMP= []
VALUES= []
comienzo = False
columns_name= []
if __name__ == "__main__":
    
    x = threading.Thread(target=readserial, args=('COM4', 115200, True, TIMESTAMP, VALUES, comienzo, columns_name))
    logging.info("Main    : before running thread")
    x.start()
    counter = 0
    index= 0
    while x.is_alive():
        #print(f"Counter: {counter} seconds")
        #counter += 1
        #print(f'{timestamp} > {data}')
        if len(VALUES) > 1:
            print("Valores: ", len(VALUES)-index)
            print("Index: ", index)
            for i in range(len(VALUES)-index):
                print(VALUES[index+i])
            index +=i
            #TIMESTAMP=[] 
            #VALUES=[]
        time.sleep(1)
        print(f"Counter: {counter} seconds")
        counter += 1
        if hasattr(x, 'result') and x.result:
            print(f"Serial Data: {x.result}")
    df = pd.DataFrame(VALUES, columns=columns_name)
    print(df.head())
    df.to_csv('data.csv', index=False)
    print('Guardando datos en data.csv')
    logging.info("Main    : Exit")
    