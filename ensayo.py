import sys
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
import pandas as pd
from manejo_serial import readserial
import threading
import configparser
from datetime import datetime


class RealTimePlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Configuración de la aplicación
        pg.setConfigOption('background', 'b')  # Fondo blanco para el gráfico
        # Leer y cargar config.ini
        self.config = configparser.ConfigParser()
        # Pedir al usuario que seleccione el archivo .ini usando un QFileDialog
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        ini_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de configuración (.ini)",
            "",
            "Archivos INI (*.ini);;Todos los archivos (*)",
            options=options
        )
        if ini_path:
            self.config.read(ini_path)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se seleccionó un archivo de configuración. La aplicación se cerrará.")
            sys.exit(1)
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
            graphWidget.setTitle(title, color="black", size="18pt")

            # Configurar el gráfico
            graphWidget.setBackground("w")  # Fondo blanco
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)

            # Inicializar datos
            buffer_size = 80*60*60  # Número de puntos en el buffer (180 segundos con 80 puntos por segundo)
            x= np.empty(buffer_size)
            x.fill(np.nan)  # Rellenar con NaN para evitar problemas de visualización
            x[0]= 0  # Establecer el primer valor en 0
            
            y = np.empty(buffer_size)
            y.fill(np.nan)  # Eje Y: valores iniciales en NaN
            y[0] = 0  # Establecer el primer valor en 0
            current_index = 0  # Índice para rastrear la posición actual en el buffer
            curve = graphWidget.plot(x, y, pen=pg.mkPen(color, width=2,connect='finite'))
            if i == 0:
                # El gráfico 0 ocupa la mitad superior (fila 0, columnas 0 a 2)
                self.layout_ensayar.addWidget(graphWidget, 0, 0, 1, 3)
            else:
                # Los gráficos 1, 2 y 3 ocupan la mitad inferior (fila 1, columnas 0, 1 y 2)
                self.layout_ensayar.addWidget(graphWidget, 1, i - 1, 1, 1)
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
        self.remaining_time= self.config.getint('Ensayo', 't_ensayo', fallback=60)  # Tiempo restante en segundos
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.remaining_time:02d} segundos')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        # Botón para parar el ensayo
        self.stop_button = QtWidgets.QPushButton("Parar Ensayo")
        self.stop_button.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(self.stop_button, 4, 2, 1, 1)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')  # Puerto serie
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)  # Baudrate
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)  # RPM del ensayo
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        self.timestamp = True
        self.tiempo_horas= []
        self.TIMESTAMP= []
        self.VALUES= []
        self.comienzo = []
        self.comienzo.append(True)  # Usar una lista para poder modificarla dentro del hilo
        self.columns_name= []
        self.index= 0
        self.ser =  threading.Thread(target=readserial, args=(self.comport, self.baudrate, self.timestamp,self.TIMESTAMP, self.VALUES, self.comienzo, self.columns_name, self.remaining_time, self.RPM_ensayo))
        self.ser.start()
        self.flag_countdown = True
        
    def parar_ensayo(self):
        # Detener el temporizador de actualización del gráfico
        self.timer.stop()
        # Detener el temporizador de cuenta regresiva
        self.countdown_timer.stop()
        # Enviar comando para detener el ensayo
        if self.ser.is_alive():
            self.comienzo[0] = False  # Cambiar el estado de comienzo a False
            self.ser.join()  # Esperar a que el hilo termine
            print("Hilo de lectura del puerto serie detenido.")
            self.close()
            
    def update_countdown(self):
        self.remaining_time -= 1
        self.countdown_label.setText(f"Tiempo restante: {self.remaining_time:02d} segundos")
        if self.remaining_time <= 0:
            self.countdown_timer.stop()

    def update_plot(self):
        
        if self.ser.is_alive():
            if len(self.VALUES) > 1:
                if self.flag_countdown:
                    self.flag_countdown = False
                    self.countdown_timer.start()
                for actual_index in range(len(self.VALUES)-self.index):
                    self.tiempo_horas.append(self.VALUES[actual_index+self.index][0])
                    self.tiempo.append(self.VALUES[actual_index+self.index][1])
                    self.temperatura_amb.append(self.VALUES[actual_index+self.index][2])
                    self.temperatura.append(self.VALUES[actual_index+self.index][3])
                    self.vueltas.append(self.VALUES[actual_index+self.index][4])
                    self.carga.append(self.VALUES[actual_index+self.index][5])
                
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
                    self.velocidad.extend([0] * (len(self.VALUES) - len(self.velocidad)))
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
                    print("Guardando datos en disco...")
                    # Crear un DataFrame de pandas
                    try:
                        df = pd.DataFrame(new_data_dict)
                        # Guardar como archivo binario (pickle)
                        output_path = "./datos_guardados_temp.pkl"
                        if not hasattr(self, 'first_save') or self.first_save:
                            df.to_pickle(output_path)
                            self.first_save = False
                        else:
                            # Leer datos existentes y concatenar
                            try:
                                df_old = pd.read_pickle(output_path)
                                df_all = pd.concat([df_old, df], ignore_index=True)
                                df_all.to_pickle(output_path)
                            except Exception as e:
                                print(f"Error al leer archivo binario existente: {e}")
                                df.to_pickle(output_path)
                    except ValueError as e:
                        print(f"Error al crear DataFrame: {e}")
                        return
                    
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
                for i, (graphWidget, curve, x, y, current_index) in enumerate(self.graphs):
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
                        curve.setDownsampling(auto=True)
                        curve.setClipToView(True)
                        # Submuestreo para todos los gráficos excepto la carga (i == 0)
                        if i==0 and current_index > 8:
                            # Submuestrear a 10 veces menos
                            x_sub = x[:current_index][::8]
                            y_sub = y[:current_index][::8]
                            curve.setData(x_sub, y_sub)
                        elif i != 0 and current_index > 80:
                            # Submuestrear a 10 veces menos
                            x_sub = x[:current_index][::80]
                            y_sub = y[:current_index][::80]
                            curve.setData(x_sub, y_sub)
                            
                        else:
                            # Para la carga, mostrar todos los datos
                            if current_index > 0:
                                curve.setData(x[:current_index], y[:current_index])
                        self.graphs[i] = (graphWidget, curve, x, y, current_index)
        
        else:
            self.timer.stop()
            print("Murio el hilo")
            self.close()
            
    def closeEvent(self, event):
        # Guardar los datos en un archivo Excel
        # Abrir el archivo binario y guardarlo como xlsx
        if self.ser.is_alive():
            self.comienzo[0] = False  # Cambiar el estado de comienzo a False
            self.ser.join()  # Esperar a que el hilo termine
            print("Hilo de lectura del puerto serie detenido.")
        self.save_data()
        print("Cerrando aplicación...")
        event.accept()

    def save_data(self):
        try:
            print("Guardando datos...")
            df = pd.read_pickle("./datos_guardados_temp.pkl")
            now = datetime.now()
            fecha_hora = now.strftime("%d-%m-%Y_%H-%M")
            output_path = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}.xlsx"
            df.to_excel(output_path, index=False)
            print(f"Datos guardados en {output_path}")
        except Exception as e:
            print(f"Error al guardar datos: {e}")
        # Guardar un archivo .txt con el mismo nombre y los datos del .ini
        try:
            txt_path = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}.txt"
            with open(txt_path, "w", encoding="utf-8") as txt_file:
                txt_file.write("Datos de configuración obtenidos del archivo config.ini:\n\n")
                for section in self.config.sections():
                    txt_file.write(f"[{section}]\n")
                    for key, value in self.config.items(section):
                        txt_file.write(f"{key} = {value}\n")
                    txt_file.write("\n")
            print(f"Archivo de configuración guardado en {txt_path}")
        except Exception as e:
            print(f"Error al guardar archivo txt: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    print("Iniciando aplicación...")
    sys.exit(app.exec_())
