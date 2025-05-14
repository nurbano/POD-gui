import logging
import threading
import time
from prueba_serial import readserial
from queue import Queue

def thread_function(name):
    logging.info("Thread %s: starting", name)
    time.sleep(2)
    logging.info("Thread %s: finishing", name)
TIMESTAMP= []
VALUES= []
comienzo = False
if __name__ == "__main__":
    
    x = threading.Thread(target=readserial, args=('COM4', 115200, True, TIMESTAMP, VALUES, comienzo))
    logging.info("Main    : before running thread")
    x.start()
    counter = 0
    while x.is_alive():
        print(f"Counter: {counter} seconds")
        counter += 1
        #print(f'{timestamp} > {data}')
        if len(TIMESTAMP) > 5 and len(VALUES) > 5:
            print('\n'.join(f'{t} > {v}' for t, v in zip(TIMESTAMP[-5:-1], VALUES[-5:-1])))
        
        time.sleep(1)
        if hasattr(x, 'result') and x.result:
            print(f"Serial Data: {x.result}")
    logging.info("Main    : Exit")
    