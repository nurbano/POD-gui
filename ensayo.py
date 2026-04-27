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

class RealTimePlot(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
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
            
        self.setWindowTitle("Tribómetro - Gráfico en Tiempo Real")
        self.setGeometry(100, 100, 1000, 700)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        
        self.datos_graficos= [ 
            ("Carga", "Carga (kg)", "g", 0, 1000),
            ("Temp. Amb.", "T[ºC]", "b", 0, 40),
            ("Tempe. Ensayo", "T[ºC]", "y", 0, 80),
            ("Velocidad", "RPM", "r", 0, 1000), 
        ]
        
        self.window_size = 80 * 180 
        self.plot_time = np.zeros(self.window_size)
        self.plot_carga = np.zeros(self.window_size)
        self.plot_temp_amb = np.zeros(self.window_size)
        self.plot_temp_obj = np.zeros(self.window_size)
        self.plot_velocidad = np.zeros(self.window_size)
        self.plot_vueltas = np.zeros(self.window_size)
        self.data_count = 0 
        
        self.curves = []
        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="14pt")
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)
            graphWidget.setYRange(min_val, max_val)

            # Evitar auto-rango en el eje Y para que no salte con picos de ruido
            graphWidget.getViewBox().disableAutoRange(axis=pg.ViewBox.YAxis)

            # Curva limpia y cruda, sin sobre-optimizar
            curve = graphWidget.plot([], [], pen=pg.mkPen(color, width=2))
            self.curves.append(curve)
            
            if i == 0:
                self.layout_ensayar.addWidget(graphWidget, 0, 0, 1, 3)
            else:
                self.layout_ensayar.addWidget(graphWidget, 1, i - 1, 1, 1)

        # Temporizadores UI
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)  # Bajamos a 5 FPS (200ms) para darle oxígeno al hilo principal
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)
        
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

        # === ARCHIVO TEMPORAL ===
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y_%H-%M")
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}_temp.csv"

        # === HILO DEL PUERTO SERIE ===
        self.data_queue = queue.Queue()
        self.comienzo = [True]
        self.flag_countdown = True
        
        self.ser = threading.Thread(
            target=readserial, 
            # Le pasamos la ruta del CSV para que el hilo lo maneje
            args=(self.comport, self.baudrate, self.data_queue, self.comienzo, self.csv_filename, self.remaining_time, self.RPM_ensayo)
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

        nuevos_datos = []
        
        # Vaciar la cola generada por el hilo serial en los últimos 200ms
        while not self.data_queue.empty():
            try:
                nuevos_datos.append(self.data_queue.get_nowait())
            except queue.Empty:
                break

        n = len(nuevos_datos) 
        
        if n > 0:
            if self.flag_countdown:
                self.flag_countdown = False
                self.countdown_timer.start()
            
            # Mover la ventana UNA SOLA VEZ
            self.plot_time = np.roll(self.plot_time, -n)
            self.plot_carga = np.roll(self.plot_carga, -n)
            self.plot_temp_amb = np.roll(self.plot_temp_amb, -n)
            self.plot_temp_obj = np.roll(self.plot_temp_obj, -n)
            self.plot_vueltas = np.roll(self.plot_vueltas, -n)

            # Rellenar los espacios vacíos
            for i, datos in enumerate(nuevos_datos):
                tiempo_ms, temp_amb, temp_obj, vueltas, carga = datos
                idx = -n + i  
                
                self.plot_time[idx] = tiempo_ms / 1000.0
                self.plot_carga[idx] = carga
                self.plot_temp_amb[idx] = temp_amb
                self.plot_temp_obj[idx] = temp_obj
                self.plot_vueltas[idx] = vueltas

            self.data_count += n

            # Calcular RPM
            if self.data_count > 40:
                delta_vueltas = self.plot_vueltas[-1] - self.plot_vueltas[-41]
                delta_tiempo = self.plot_time[-1] - self.plot_time[-41]
                rpm = (delta_vueltas / delta_tiempo) * 60.0 if delta_tiempo > 0 else 0
            else:
                rpm = 0

            self.plot_velocidad = np.roll(self.plot_velocidad, -n)
            self.plot_velocidad[-n:] = rpm 

            pts = min(self.data_count, self.window_size)
            
            # Redibujar curvas limpias
            self.curves[0].setData(self.plot_time[-pts:], self.plot_carga[-pts:])
            self.curves[1].setData(self.plot_time[-pts:], self.plot_temp_amb[-pts:])
            self.curves[2].setData(self.plot_time[-pts:], self.plot_temp_obj[-pts:])
            self.curves[3].setData(self.plot_time[-pts:], self.plot_velocidad[-pts:])

    def closeEvent(self, event):
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive():
            self.ser.join()
            
        self.save_data()
        event.accept()

    def save_data(self):
        try:
            print("Procesando y guardando datos en Excel...")
            # Leer el CSV final que creó el hilo serial
            df = pd.read_csv(self.csv_filename)
            excel_path = self.csv_filename.replace('_temp.csv', '.xlsx')
            df.to_excel(excel_path, index=False)
            print(f"✅ Excel guardado exitosamente en: {excel_path}")
            
            # Como ya está a salvo en Excel, podemos borrar el temporal
            # os.remove(self.csv_filename) 
        except Exception as e:
            print(f"❌ Error al crear el archivo Excel: {e}")
            print(f"Los datos crudos están a salvo en: {self.csv_filename}")

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