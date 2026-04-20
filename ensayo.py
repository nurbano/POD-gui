import sys
import os
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore
import pandas as pd
from manejo_serial import readserial
import threading
import configparser
from datetime import datetime
import queue
import csv

class RealTimePlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # Configuración de la aplicación
        pg.setConfigOption('background', 'w')  # Fondo blanco para el gráfico (mejor visibilidad)
        pg.setConfigOption('foreground', 'k')  # Texto en negro
        
        # Leer y cargar config.ini
        self.config = configparser.ConfigParser()
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        ini_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de configuración (.ini)", "", "Archivos INI (*.ini);;Todos los archivos (*)", options=options
        )
        if ini_path:
            self.config.read(ini_path)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se seleccionó un archivo de configuración. La aplicación se cerrará.")
            sys.exit(1)
            
        # Configuración de la ventana
        self.setWindowTitle("Tribómetro - Gráfico en Tiempo Real")
        self.setGeometry(100, 100, 1000, 700)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        
        self.datos_graficos= [ 
            ("Carga", "Carga (kg)", "g", 0, 1000),
            ("Temp. Amb.", "T[ºC]", "b", 0, 40),
            ("Tempe. Ensayo", "T[ºC]", "y", 0, 80), # Aumenté un poco la escala de temp ensayo
            ("Velocidad", "RPM", "r", 0, 1000), # Ajustado para 800 RPM
        ]
        
        # === CONFIGURACIÓN DE LA VENTANA DESLIZANTE ===
        # Mostrar los últimos 3 minutos (180 seg) a 80 SPS = ~14.400 puntos.
        self.window_size = 80 * 180 
        self.plot_time = np.zeros(self.window_size)
        self.plot_carga = np.zeros(self.window_size)
        self.plot_temp_amb = np.zeros(self.window_size)
        self.plot_temp_obj = np.zeros(self.window_size)
        self.plot_velocidad = np.zeros(self.window_size)
        self.plot_vueltas = np.zeros(self.window_size)
        self.data_count = 0  # Contador de muestras recibidas
        
        # Crear gráficos
        self.curves = []
        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="14pt")
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)
            graphWidget.setYRange(min_val, max_val)

            # Crear la curva vacía
            curve = graphWidget.plot([], [], pen=pg.mkPen(color, width=2))
            self.curves.append(curve)
            
            if i == 0:
                self.layout_ensayar.addWidget(graphWidget, 0, 0, 1, 3) # Carga arriba
            else:
                self.layout_ensayar.addWidget(graphWidget, 1, i - 1, 1, 1) # Resto abajo

        # Temporizadores UI
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)  # Actualizar gráficos cada 100 ms (10 FPS)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)
        
        # Variables de config
        self.remaining_time = self.config.getint('Ensayo', 't_ensayo', fallback=60)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.remaining_time:02d} segundos')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        
        self.stop_button = QtWidgets.QPushButton("Parar Ensayo")
        self.stop_button.setStyleSheet("font-size: 14pt; background-color: #ff4c4c; color: white;")
        self.stop_button.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(self.stop_button, 4, 2, 1, 1)

        # === DATALOGGER (Guardado continuo en CSV) ===
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y_%H-%M")
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}_temp.csv"
        self.csv_file = open(self.csv_filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["Tiempo(ms)", "TempAmb(C)", "TempObj(C)", "Vueltas", "Carga"])

        # === HILO DEL PUERTO SERIE ===
        self.data_queue = queue.Queue()
        self.comienzo = [True]
        self.flag_countdown = True
        
        self.ser = threading.Thread(
            target=readserial, 
            args=(self.comport, self.baudrate, self.data_queue, self.comienzo, self.remaining_time, self.RPM_ensayo)
        )
        self.ser.start()

    def parar_ensayo(self):
        self.timer.stop()
        self.countdown_timer.stop()
        if self.ser.is_alive():
            self.comienzo[0] = False
            self.ser.join()
        self.close()
            
    def update_countdown(self):
        self.remaining_time -= 1
        self.countdown_label.setText(f"Tiempo restante: {self.remaining_time:02d} segundos")
        if self.remaining_time <= 0:
            self.countdown_timer.stop()

    def update_plot(self):
        if not self.ser.is_alive() and self.data_queue.empty():
            self.timer.stop()
            self.close()
            return

        nuevos_datos = False
        
        # Extraer TODOS los datos acumulados en la cola durante los últimos 100ms
        while not self.data_queue.empty():
            try:
                # datos = (tiempo, temp_amb, temp_obj, vueltas, carga)
                datos = self.data_queue.get_nowait()
                nuevos_datos = True
                
                tiempo_ms, temp_amb, temp_obj, vueltas, carga = datos
                tiempo_s = tiempo_ms / 1000.0
                
                # 1. Guardar en disco inmediatamente
                self.csv_writer.writerow([tiempo_ms, temp_amb, temp_obj, vueltas, carga])

                # 2. Desplazar la ventana y agregar nuevos datos
                self.plot_time = np.roll(self.plot_time, -1)
                self.plot_carga = np.roll(self.plot_carga, -1)
                self.plot_temp_amb = np.roll(self.plot_temp_amb, -1)
                self.plot_temp_obj = np.roll(self.plot_temp_obj, -1)
                self.plot_vueltas = np.roll(self.plot_vueltas, -1)

                self.plot_time[-1] = tiempo_s
                self.plot_carga[-1] = carga
                self.plot_temp_amb[-1] = temp_amb
                self.plot_temp_obj[-1] = temp_obj
                self.plot_vueltas[-1] = vueltas

                self.data_count += 1
            except queue.Empty:
                break

        # Si entraron datos, actualizamos los gráficos
        if nuevos_datos:
            if self.flag_countdown:
                self.flag_countdown = False
                self.countdown_timer.start()

            # Calcular RPM (derivada de los últimos ~0.5 segundos = 40 muestras)
            if self.data_count > 40:
                delta_vueltas = self.plot_vueltas[-1] - self.plot_vueltas[-41]
                delta_tiempo = self.plot_time[-1] - self.plot_time[-41]
                rpm = (delta_vueltas / delta_tiempo) * 60.0 if delta_tiempo > 0 else 0
            else:
                rpm = 0

            self.plot_velocidad = np.roll(self.plot_velocidad, -1)
            self.plot_velocidad[-1] = rpm

            # Determinar cuántos puntos mostrar (hasta que se llene la ventana de 3 min)
            pts = min(self.data_count, self.window_size)
            
            # 3. Redibujar curvas de manera eficiente
            self.curves[0].setData(self.plot_time[-pts:], self.plot_carga[-pts:])
            self.curves[1].setData(self.plot_time[-pts:], self.plot_temp_amb[-pts:])
            self.curves[2].setData(self.plot_time[-pts:], self.plot_temp_obj[-pts:])
            self.curves[3].setData(self.plot_time[-pts:], self.plot_velocidad[-pts:])

    def closeEvent(self, event):
        # Asegurarnos de cerrar el hilo
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive():
            self.ser.join()
            
        # Cerrar el archivo CSV temporal
        if hasattr(self, 'csv_file') and not self.csv_file.closed:
            self.csv_file.close()

        # Convertir a Excel final
        self.save_data()
        event.accept()

    def save_data(self):
        try:
            print("Procesando y guardando datos en Excel...")
            # Leer el CSV temporal que fuimos llenando
            df = pd.read_csv(self.csv_filename)
            
            # Recrear el nombre final del archivo
            excel_path = self.csv_filename.replace('_temp.csv', '.xlsx')
            df.to_excel(excel_path, index=False)
            print(f"✅ Excel guardado exitosamente en: {excel_path}")
            
            # Opcional: Eliminar el CSV temporal para ahorrar espacio
            # os.remove(self.csv_filename) 

        except Exception as e:
            print(f"❌ Error al crear el archivo Excel: {e}")
            print(f"Los datos crudos están a salvo en: {self.csv_filename}")

        # Guardar archivo .txt de configuración
        try:
            txt_path = self.csv_filename.replace('_temp.csv', '.txt')
            with open(txt_path, "w", encoding="utf-8") as txt_file:
                txt_file.write("Datos de configuración obtenidos del archivo config.ini:\n\n")
                for section in self.config.sections():
                    txt_file.write(f"[{section}]\n")
                    for key, value in self.config.items(section):
                        txt_file.write(f"{key} = {value}\n")
                    txt_file.write("\n")
        except Exception as e:
            print(f"Error al guardar archivo txt: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    sys.exit(app.exec_())