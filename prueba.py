import sys
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
import pandas as pd
import atexit
import time
from prueba_serial import readserial, begin_test
import threading


class RealTimePlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana
        self.setWindowTitle("Gráfico en Tiempo Real (60 segundos)")
        self.setGeometry(100, 100, 800, 600)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        self.datos_graficos= [ 
                        ("Carga", "Carga (kg)", "g", 0, 10000),
                        ("Temp. Amb.", "T[ºC]", "b", 0,40),
                        ("Tempe. Ensayo", "T[ºC]", "y", 0, 40),
                         ("Velocidad", "RPM", "r", 0, 300),
                         
                         ]
        # Crear un gráfico para cada variable
        self.graphs = np.empty((4,), dtype=object)
        self.data = []
        self.temperatura = []
        self.carga = []
        self.humedad = []
        self.velocidad = []
        self.tiempo= []

        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            # Crear un widget de gráfico
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="20pt")

            # Configurar el gráfico
            graphWidget.setBackground("w")  # Fondo blanco
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)

            # Inicializar datos
            buffer_size = 1600*3  # Número de puntos en el buffer (60 segundos con 10 puntos por segundo)
            x = np.linspace(0, 180, buffer_size)  # Eje X: 60 segundos
            y = np.zeros(buffer_size)  # Eje Y: valores iniciales en cero
            current_index = 0  # Índice para rastrear la posición actual en el buffer
            curve = graphWidget.plot(x, y, pen=pg.mkPen(color, width=2))
            self.layout_ensayar.addWidget(graphWidget, i // 2, i % 2)
            graphWidget.setYRange(min_val, max_val)
            graphWidget.setXRange(0, 60)
            self.graphs[i] = (graphWidget, curve, x, y, current_index)
        # Configurar un temporizador para actualizar el gráfico
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)  # Intervalo de actualización en milisegundos (100 ms = 0.1 s)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_label = QtWidgets.QLabel("Tiempo restante: 60  segundos")
        self.remaining_time = 60 # 60 segundos
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        self.countdown_timer.start()
        #Abro el puerto serie
        self.comport = 'COM4'
        self.baudrate = 115200
        self.timestamp = True
        self.TIMESTAMP= []
        self.VALUES= []
        self.comienzo = False
        self.columns_name= []
        self.index= 0
        self.ser =  threading.Thread(target=readserial, args=(self.comport, self.baudrate, self.timestamp,self.TIMESTAMP, self.VALUES, self.comienzo, self.columns_name))
        self.ser.start()
        

    def update_countdown(self):
        #print("hola")
        self.remaining_time -= 1
        # minutes = self.remaining_time // 60
        # seconds = self.remaining_time % 60
        # self.countdown_label.setText(f"Tiempo restante: {minutes:02d}:{seconds:02d}")
        self.countdown_label.setText(f"Tiempo restante: {self.remaining_time:02d} segundos")
        if self.remaining_time <= 0:
            self.countdown_timer.stop()
            self.close()


    def update_plot(self):
        #start_time = time.time()
        if self.ser.is_alive():
            #print("Valores: ", len(self.VALUES))
            #print("Index: ", index)
            if len(self.VALUES) > 1:
                for actual_index in range(len(self.VALUES)-self.index):
                    #print(self.VALUES[i])
                    self.tiempo.append(self.VALUES[actual_index+self.index][0])
                    self.carga.append(self.VALUES[actual_index+self.index][1])
                    self.temperatura.append(self.VALUES[actual_index+self.index][2])
                    self.humedad.append(self.VALUES[actual_index+self.index][3])
                    self.velocidad.append(self.VALUES[actual_index+self.index][4])
                self.index +=actual_index
            #self.TIMESTAMP=[] 
            #self.VALUES=[]
                self.tiempo.append(len(self.tiempo) * 0.1)
                for i, (graphWidget, curve, x, y, current_index) in enumerate(self.graphs):
                    # Generar un nuevo valor aleatorio (puedes reemplazar esto con tus datos reales)
                    #min_val, max_val = self.random_data[self.datos_graficos[i][0]]
                    #new_value = np.random.uniform(min_val, max_val)
                    #x= self.tiempo[-actual_index]
                    if i== 0:
                        new_value= self.carga[-actual_index:-1]
                    elif i== 1:
                        new_value= self.temperatura[-actual_index:-1]
                    elif i== 2:
                        new_value= self.humedad[-actual_index:-1]
                    elif i== 3:
                        new_value= self.velocidad[-actual_index:-1]

                    data_lists = [self.carga, self.temperatura, self.humedad, self.velocidad]
                    #data_lists[i].append(new_value)
                    # Añadir el nuevo valor al final del buffer
                    for j in range(len(new_value)):
                        if current_index < len(y):
                            y[current_index] = new_value[j]
                            current_index += 1
                        else:
                            # Si el buffer está lleno, desplazar los valores hacia la izquierda
                            y[:-1] = y[1:]
                            y[-1] = new_value[j]

                        # Actualizar la curva
                        curve.setData(x, y)
                        self.graphs[i] = (graphWidget, curve, x, y, current_index)
        #end_time = time.time()
       # print(end_time - start_time )
        #print("Tiempo de actualización:", end_time - start_time, "segundos")
    def closeEvent(self, event):
        # Guardar los datos en un archivo Excel
        data_dict = {
            "Tiempo (s)": self.tiempo,
            "Carga (kg)": self.carga,
            "Temperatura (ºC)": self.temperatura,
            "Humedad (%)": self.humedad,
            "Velocidad (m/s)": self.velocidad
        }
        df = pd.DataFrame(data_dict)
        output_path = "./datos_guardados.xlsx"
        df.to_excel(output_path, index=False)
        print(f"Datos guardados en {output_path}")
        event.accept()
        # Cerrar la aplicación
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    print("Iniciando aplicación...")
    sys.exit(app.exec_())
