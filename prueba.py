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
                        ("Carga", "Carga (kg)", "g", 0, 1000),
                        ("Temp. Amb.", "T[ºC]", "b", 0,40),
                        ("Tempe. Ensayo", "T[ºC]", "y", 0, 40),
                         ("Velocidad", "RPM", "r", 0, 300),
                         
                         ]
        # Crear un gráfico para cada variable
        self.graphs = np.empty((4,), dtype=object)
        self.data = []
        self.temperatura = []
        self.carga = []
        self.temperatura_amb = []
        self.velocidad = []
        self.vueltas = []
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
            buffer_size = 80*60*60  # Número de puntos en el buffer (180 segundos con 80 puntos por segundo)
            #x = np.linspace(0, 60, buffer_size)  # Eje X: 60 segundos
            x= np.empty(buffer_size)
            x.fill(np.nan)  # Rellenar con NaN para evitar problemas de visualización
            y = np.empty(buffer_size)
            y.fill(np.nan)  # Eje Y: valores iniciales en NaN
            #y = np.zeros(buffer_size)  # Eje Y: valores iniciales en cero
            current_index = 0  # Índice para rastrear la posición actual en el buffer
            curve = graphWidget.plot(x, y, pen=pg.mkPen(color, width=2,connect='finite'))
            self.layout_ensayar.addWidget(graphWidget, i // 2, i % 2)
            graphWidget.setYRange(min_val, max_val)
            #graphWidget.setXRange(0, 60)
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
        self.remaining_time = 910 # 60 segundos
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        self.countdown_timer.start()
        #Abro el puerto serie
        self.comport = 'COM4'
        self.baudrate = 115200
        self.timestamp = True
        self.tiempo_horas= []
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
                    #print(actual_index, self.VALUES[actual_index+self.index])
                    #"tiempoMs,tempAmbC,tempObjC,vueltas,celdaCarga"
                    self.tiempo_horas.append(self.VALUES[actual_index+self.index][0])
                    self.tiempo.append(self.VALUES[actual_index+self.index][1])
                    self.temperatura_amb.append(self.VALUES[actual_index+self.index][2])
                    self.temperatura.append(self.VALUES[actual_index+self.index][3])
                    self.vueltas.append(self.VALUES[actual_index+self.index][4])
                    self.carga.append(self.VALUES[actual_index+self.index][5])
                    # Guardar datos en disco cada 1000 muestras y limpiar listas para evitar uso excesivo de memoria
                save_interval = 5000
                if len(self.vueltas) >= 30:
                        # Diferencia de vueltas en los últimos 3 puntos
                        delta_vueltas = self.vueltas[-1] - self.vueltas[-31] if len(self.vueltas) > 30 else self.vueltas[-1] - self.vueltas[0]
                        # Diferencia de tiempo en milisegundos
                        delta_tiempo = self.tiempo[-1] - self.tiempo[-31] if len(self.tiempo) > 30 else self.tiempo[-1] - self.tiempo[0]
                        if delta_tiempo > 0:
                            # Velocidad en vueltas por segundo (Hz)
                            velocidad = delta_vueltas / (delta_tiempo / 60000.0)
                        else:
                            velocidad = 0
                        self.velocidad.append(velocidad)
                else:
                    self.velocidad.append(0)
                self.index +=actual_index+1
                if len(self.tiempo) >= save_interval:
                    print(len(self.tiempo_horas), len(self.tiempo), len(self.carga), len(self.temperatura), len(self.temperatura_amb), len(self.vueltas))
                    print(self.tiempo_horas[-1], self.tiempo[-1], self.temperatura_amb[-1], self.temperatura[-1], self.vueltas[-1], self.carga[-1])
                    new_data_dict = {
                        "Timestamp": self.tiempo_horas,
                        "Tiempo (ms)": self.tiempo,
                        "Carga (kg)": self.carga,
                        "Temperatura (ºC)": self.temperatura,
                        "Tempratura Amb. (ºC)": self.temperatura_amb,
                        "Vueltas": self.vueltas
                    }
                    # for k, v in new_data_dict.items():
                    #     print(f"{k}: {len(v)}")
                    print("Guardando datos en disco...")
                    # Crear un DataFrame de pandas
                    df = pd.DataFrame(new_data_dict)
                    # Guardar en modo append si el archivo ya existe
                    output_path = "./datos_guardados_temp.xlsx"
                    if not hasattr(self, 'first_save') or self.first_save:
                        df.to_excel(output_path, index=False)
                        self.first_save = False
                    else:
                        with pd.ExcelWriter(output_path, mode='a', if_sheet_exists='overlay', engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, header=False, startrow=writer.sheets['Sheet1'].max_row)
                    # Mantener solo los últimos 100 datos en memoria
                    keep = 100
                    self.tiempo_horas = self.tiempo_horas[-keep:]
                    self.tiempo = self.tiempo[-keep:]
                    self.carga = self.carga[-keep:]
                    self.temperatura = self.temperatura[-keep:]
                    self.temperatura_amb = self.temperatura_amb[-keep:]
                    self.velocidad = self.velocidad[-keep:]
                    self.vueltas = self.vueltas[-keep:]
                    # Limitar el tamaño de VALUES para que no crezca indefinidamente
                    max_values_length = 5000  # Puedes ajustar este valor según lo necesario
                    #print(f"Longitud de VALUES: {len(self.VALUES)}, Max: {max_values_length}")
                    if len(self.VALUES) > max_values_length:
                        eliminate_length = int(max_values_length*0.2)  # Eliminar el 20% de los datos más antiguos
                        del self.VALUES[:eliminate_length]
                        print("Valores eliminados para evitar crecimiento indefinido")
                        self.index -= eliminate_length
                    #print(self.tiempo_horas[-1], self.tiempo[-1], self.temperatura_amb[-1], self.temperatura[-1], self.vueltas[-1], self.carga[-1])
                    # actual_index es el número de nuevos datos procesados en este ciclo.
                    # Se usa para saber cuántos elementos nuevos se han añadido y actualizar self.index.
                    # No necesitas modificarlo, solo asegúrate de que después del for, hagas:
                #self.index += actual_index
                    # Calcular velocidad a partir del incremento de las últimas 3 vueltas
                    
            #self.TIMESTAMP=[] 
            #self.VALUES=[]
                #self.tiempo.append(len(self.tiempo) * 0.1)
                for i, (graphWidget, curve, x, y, current_index) in enumerate(self.graphs):
                    # Generar un nuevo valor aleatorio (puedes reemplazar esto con tus datos reales)
                    #min_val, max_val = self.random_data[self.datos_graficos[i][0]]
                    #new_value = np.random.uniform(min_val, max_val)
                    #x= self.tiempo[-actual_index]
                    tiempo_actual=self.tiempo[-actual_index:-1]
                    if i== 0:
                        new_value= self.carga[-actual_index:-1]
                    elif i== 1:
                        new_value= self.temperatura[-actual_index:-1]
                    elif i== 2:
                        new_value= self.temperatura_amb[-actual_index:-1]
                    elif i== 3:
                        new_value= self.velocidad[-actual_index:-1]

                    
                    # Añadir el nuevo valor al final del buffer
                    for j in range(len(new_value)):
                        if current_index < len(y):
                            y[current_index] = new_value[j]
                            x[current_index] = tiempo_actual[j]/1000
                            current_index += 1
                        else:
                            # Si el buffer está lleno, desplazar los valores hacia la izquierda
                            print("Buffer lleno, desplazando valores")
                            y[:-1] = y[1:]
                            x[:-1] = x[1:]
                            y[-1] = new_value[j]
                            x[-1] = tiempo_actual[j]

                        # Actualizar la curva
                        #print("x: ", x[current_index])
                        #curve.setData(x, y)
                        curve.setDownsampling(auto=True)
                        curve.setClipToView(True)
                        # Submuestreo para todos los gráficos excepto la carga (i == 0)
                        #print(f"Actualizando gráfico {i} con {current_index} puntos")
                        if i==0 and current_index > 8:
                            # Submuestrear a 10 veces menos
                            #print("Submuestreando carga")
                            x_sub = x[:current_index][::8]
                            y_sub = y[:current_index][::8]
                            curve.setData(x_sub, y_sub)
                        elif i != 0 and current_index > 80:
                            # Submuestrear a 10 veces menos
                            #print("Submuestreando temperatura")
                            x_sub = x[:current_index][::80]
                            y_sub = y[:current_index][::80]
                            curve.setData(x_sub, y_sub)
                        else:
                            # Para la carga, mostrar todos los datos
                            print("Actualizando carga sin submuestreo")
                            curve.setData(x[:current_index], y[:current_index])
                        self.graphs[i] = (graphWidget, curve, x, y, current_index)
        
        if self.ser.is_alive == False:
            print("Murio el hilo")
            # Aquí puedes agregar cualquier acción adicional que desees realizar al finalizar la lectura del puerto serie
        
        #end_time = time.time()
       # print(end_time - start_time )
        #print("Tiempo de actualización:", end_time - start_time, "segundos")
    def closeEvent(self, event):
        # Guardar los datos en un archivo Excel
        data_dict = {
            "Timestamp": self.tiempo_horas,
            "Tiempo (ms)": self.tiempo,
            "Carga (kg)": self.carga,
            "Temperatura (ºC)": self.temperatura,
            "Tempratura Amb. (ºC)": self.temperatura_amb,
            "Vueltas": self.vueltas
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
