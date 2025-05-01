import sys
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
import pandas as pd
import atexit
import time

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
        self.datos_graficos= [ ("Carga", "Carga (kg)", "b"),
                        ("Temperatura", "T[ºC]", "y"), 
                         ("Humedad", "Hum. %", "r"),
                         ("Velocidad", "Vel. m/s", "g")
                         ]
        # Crear un gráfico para cada variable
        self.graphs = np.empty((4,), dtype=object)
        self.data = []
        self.temperatura = []
        self.carga = []
        self.humedad = []
        self.velocidad = []
        self.tiempo= []
        self.random_data = {"Carga": [0,10], "Temperatura": [0,35], "Humedad": [20,30], "Velocidad": [100, 200]}
        self.random_data_fn= {
            "Carga": np.sin(np.linspace(0, 2 * np.pi, 100)),
            "Temperatura": np.cos(np.linspace(0, 2 * np.pi, 100)),
            "Humedad": np.random.rand(100),
            "Velocidad": np.random.rand(100)}
        self.data_range = {
            "Carga": [0, 30],
            "Temperatura": [0, 50],
            "Humedad": [0, 100],
            "Velocidad": [0, 300]
        }
        for i, (title, y_label, color) in enumerate(self.datos_graficos):
            # Crear un widget de gráfico
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="20pt")

            # Configurar el gráfico
            graphWidget.setBackground("w")  # Fondo blanco
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)

            # Inicializar datos
            buffer_size = 600  # Número de puntos en el buffer (60 segundos con 10 puntos por segundo)
            x = np.linspace(0, 60, buffer_size)  # Eje X: 60 segundos
            y = np.zeros(buffer_size)  # Eje Y: valores iniciales en cero
            current_index = 0  # Índice para rastrear la posición actual en el buffer

            # Crear la curva
            curve = graphWidget.plot(x, y, pen=pg.mkPen(color, width=2))
            self.layout_ensayar.addWidget(graphWidget, i // 2, i % 2)

            # Configurar el rango del eje X para mostrar solo los últimos 60 segundos
            # graphWidget.setXRange(0, 60)
            # Configurar el rango del eje Y según los datos
            min_val, max_val = self.data_range[title]
            graphWidget.setYRange(min_val, max_val)
            # graphWidget.setYRange(0, 1)

            graphWidget.setXRange(0, 60)
            #graphWidget.setYRange(0, 1)
            # Almacenar el gráfico y los datos
            #self.graphs.append((graphWidget, curve, x, y, current_index))
            self.graphs[i] = (graphWidget, curve, x, y, current_index)
        # Configurar un temporizador para actualizar el gráfico
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)  # Intervalo de actualización en milisegundos (100 ms = 0.1 s)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        # self.timer_finish = QtCore.QTimer()
        # self.timer_finish.setInterval(60000)  # Intervalo de actualización en milisegundos (100 ms = 0.1 s)
        # self.timer_finish.timeout.connect(self.close)
        # self.timer_finish.start()
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_label = QtWidgets.QLabel("Tiempo restante: 60  segundos")
        self.remaining_time = 60 # 60 segundos
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        self.countdown_timer.start()

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
        self.tiempo.append(len(self.tiempo) * 0.1)
        for i, (graphWidget, curve, x, y, current_index) in enumerate(self.graphs):
            # Generar un nuevo valor aleatorio (puedes reemplazar esto con tus datos reales)
            min_val, max_val = self.random_data[self.datos_graficos[i][0]]
            new_value = np.random.uniform(min_val, max_val)

            data_lists = [self.carga, self.temperatura, self.humedad, self.velocidad]
            data_lists[i].append(new_value)
            # Añadir el nuevo valor al final del buffer
            if current_index < len(y):
                y[current_index] = new_value
                current_index += 1
            else:
                # Si el buffer está lleno, desplazar los valores hacia la izquierda
                y[:-1] = y[1:]
                y[-1] = new_value

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
