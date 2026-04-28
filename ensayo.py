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
        # Configuración visual de los gráficos
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        # Leer archivo de configuración
        self.config = configparser.ConfigParser()
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        ini_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de configuración (.ini)", "", "Archivos INI (*.ini);;Todos los archivos (*)", options=options
        )
        if ini_path:
            self.config.read(ini_path)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se seleccionó un archivo de configuración.")
            sys.exit(1)
            
        # Configuración de la ventana principal
        self.setWindowTitle("Tribómetro - Adquisición Industrial")
        self.setGeometry(100, 100, 1000, 700)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        
        self.datos_graficos = [ 
            ("Carga", "Carga (kg)", "g", 0, 1000),
            ("Temp. Amb.", "T[ºC]", "b", 0, 40),
            ("Tempe. Ensayo", "T[ºC]", "y", 0, 80),
            ("Velocidad", "RPM", "r", 0, 1000), 
        ]
        
        # === BUFFER DE VENTANA DESLIZANTE ===
        self.window_seconds = 180
        self.window_size = 80 * self.window_seconds 
        self.plot_time = np.zeros(self.window_size)
        self.plot_carga = np.zeros(self.window_size)
        self.plot_temp_amb = np.zeros(self.window_size)
        self.plot_temp_obj = np.zeros(self.window_size)
        self.plot_velocidad = np.zeros(self.window_size)
        self.plot_vueltas = np.zeros(self.window_size)
        self.data_count = 0 
        
        self.curves = []
        self.graph_widgets = []

        # Creación de los gráficos
        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="12pt")
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)
            graphWidget.setYRange(min_val, max_val)

            # Desactivar el auto-rango
            graphWidget.getViewBox().disableAutoRange()

            curve = graphWidget.plot([], [], pen=pg.mkPen(color, width=2))
            self.curves.append(curve)
            self.graph_widgets.append(graphWidget)
            
            if i == 0:
                self.layout_ensayar.addWidget(graphWidget, 0, 0, 1, 3) 
            else:
                self.layout_ensayar.addWidget(graphWidget, 1, i - 1, 1, 1) 

        # Temporizador ÚNICO de la Interfaz (5 FPS)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        
        # Carga de parámetros desde config.ini
        self.total_ensayo_s = self.config.getint('Ensayo', 't_ensayo', fallback=60)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        
        # Etiqueta de tiempo (Ahora arranca con el tiempo total)
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.total_ensayo_s:02d} segundos')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        
        self.stop_button = QtWidgets.QPushButton("Parar Ensayo")
        self.stop_button.setStyleSheet("font-size: 14pt; background-color: #d9534f; color: white; padding: 10px;")
        self.stop_button.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(self.stop_button, 4, 2, 1, 1)

        # Nombre del archivo temporal
        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y_%H-%M")
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}_temp.csv"

        # === INICIO DEL HILO DE ADQUISICIÓN ===
        self.data_queue = queue.Queue()
        self.comienzo = [True]
        
        self.ser = threading.Thread(
            target=readserial, 
            args=(self.comport, self.baudrate, self.data_queue, self.comienzo, self.csv_filename, self.total_ensayo_s, self.RPM_ensayo)
        )
        self.ser.start()

    def parar_ensayo(self):
        self.timer.stop()
        if self.ser.is_alive():
            self.comienzo[0] = False
            self.ser.join()
        self.close()

    def update_plot(self):
        if not self.ser.is_alive() and self.data_queue.empty():
            self.timer.stop()
            self.close()
            return

        nuevos_datos = []
        # Vaciar la cola de datos recibidos desde el hilo serial
        while not self.data_queue.empty():
            try:
                nuevos_datos.append(self.data_queue.get_nowait())
            except queue.Empty:
                break

        n = len(nuevos_datos) 
        
        if n > 0:
            # === ACTUALIZACIÓN DEL TIEMPO RESTANTE (HARDWARE TIMING) ===
            # Tomamos el tiempo del último paquete recibido en este lote
            tiempo_actual_ms = nuevos_datos[-1][0]
            tiempo_restante_s = max(0, int(self.total_ensayo_s - (tiempo_actual_ms / 1000.0)))
            self.countdown_label.setText(f"Tiempo restante: {tiempo_restante_s:02d} segundos")

            # Desplazamiento de los arrays mediante un único np.roll
            self.plot_time = np.roll(self.plot_time, -n)
            self.plot_carga = np.roll(self.plot_carga, -n)
            self.plot_temp_amb = np.roll(self.plot_temp_amb, -n)
            self.plot_temp_obj = np.roll(self.plot_temp_obj, -n)
            self.plot_vueltas = np.roll(self.plot_vueltas, -n)

            # Inserción de los nuevos datos en el final del buffer
            for i, datos in enumerate(nuevos_datos):
                tiempo_ms, temp_amb, temp_obj, vueltas, carga = datos
                idx = -n + i  
                self.plot_time[idx] = tiempo_ms / 1000.0
                self.plot_carga[idx] = carga
                self.plot_temp_amb[idx] = temp_amb
                self.plot_temp_obj[idx] = temp_obj
                self.plot_vueltas[idx] = vueltas

            self.data_count += n

            # Cálculo de RPM suavizado
            if self.data_count > 40:
                delta_vueltas = self.plot_vueltas[-1] - self.plot_vueltas[-41]
                delta_tiempo = self.plot_time[-1] - self.plot_time[-41]
                rpm = (delta_vueltas / delta_tiempo) * 60.0 if delta_tiempo > 0 else 0
            else:
                rpm = 0

            self.plot_velocidad = np.roll(self.plot_velocidad, -n)
            self.plot_velocidad[-n:] = rpm 

            pts = min(self.data_count, self.window_size)
            
            # Actualización eficiente de los datos en las curvas
            self.curves[0].setData(self.plot_time[-pts:], self.plot_carga[-pts:])
            self.curves[1].setData(self.plot_time[-pts:], self.plot_temp_amb[-pts:])
            self.curves[2].setData(self.plot_time[-pts:], self.plot_temp_obj[-pts:])
            self.curves[3].setData(self.plot_time[-pts:], self.plot_velocidad[-pts:])

            # === CONTROL MANUAL DEL EJE X ===
            t_max = self.plot_time[-1]
            t_min = max(0, t_max - self.window_seconds)
            for gw in self.graph_widgets:
                gw.setXRange(t_min, t_max, padding=0)

    def closeEvent(self, event):
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive():
            self.ser.join()
        self.save_data()
        event.accept()

    def save_data(self):
        try:
            print("Exportando datos finales a Excel...")
            if os.path.exists(self.csv_filename):
                df = pd.read_csv(self.csv_filename)
                excel_path = self.csv_filename.replace('_temp.csv', '.xlsx')
                df.to_excel(excel_path, index=False)
                print(f"✅ Archivo guardado: {excel_path}")
        except Exception as e:
            print(f"❌ Error al exportar: {e}")

        # Guardar metadatos del ensayo
        try:
            txt_path = self.csv_filename.replace('_temp.csv', '.txt')
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"Registro de Ensayo - {self.nombre_estacion}\n")
                f.write(f"Fecha: {datetime.now()}\n\nConfiguración:\n")
                for section in self.config.sections():
                    f.write(f"[{section}]\n")
                    for k, v in self.config.items(section):
                        f.write(f"{k} = {v}\n")
                    f.write("\n")
        except Exception as e:
            print(f"Error al guardar txt: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    sys.exit(app.exec_())