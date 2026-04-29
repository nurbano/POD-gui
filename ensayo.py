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
            sys.exit(1)
            
        self.setWindowTitle("Tribómetro - Datos Calibrados")
        self.setGeometry(100, 100, 1100, 800)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        
        # --- PARÁMETROS DE CALIBRACIÓN ---
        self.factor_k = self.config.getfloat('Calibracion', 'factor_de_calibracion', fallback=1.0)
        self.cero_offset = self.config.getfloat('Calibracion', 'cero_offset', fallback=0.0)
        # ---------------------------------
        
        self.datos_graficos = [ 
            ("Carga", "Carga (Kg/N)", "g", 0, 100), # Ajustado a escala real
            ("Temp. Amb.", "T[ºC]", "b", 0, 40),
            ("Tempe. Ensayo", "T[ºC]", "y", 0, 80),
            ("Velocidad", "RPM", "r", 0, 1000), 
        ]
        
        self.window_seconds = 180
        self.window_size = 80 * self.window_seconds 
        self.plot_time, self.plot_carga = np.zeros(self.window_size), np.zeros(self.window_size)
        self.plot_temp_amb, self.plot_temp_obj = np.zeros(self.window_size), np.zeros(self.window_size)
        self.plot_velocidad, self.plot_vueltas = np.zeros(self.window_size), np.zeros(self.window_size)
        self.data_count = 0 
        
        self.current_y_mins = [0.0] * 4
        self.current_y_maxs = [10.0, 40.0, 80.0, 1000.0]
        # Piso de zoom: 2.0 unidades para carga (ej. 2kg), 5 para el resto.
        self.rangos_minimos = [2.0, 5.0, 5.0, 20.0] 

        self.curves = []
        self.graph_widgets = []

        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="12pt")
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)
            graphWidget.getAxis('left').setWidth(70) 
            graphWidget.getViewBox().disableAutoRange()
            curve = graphWidget.plot([], [], pen=pg.mkPen(color, width=2), clipToView=True, autoDownsample=True)
            self.curves.append(curve)
            self.graph_widgets.append(graphWidget)
            self.layout_ensayar.addWidget(graphWidget, 0 if i==0 else 1, 0 if i==0 else i-1, 1, 3 if i==0 else 1)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        
        self.total_ensayo_s = self.config.getint('Ensayo', 't_ensayo', fallback=60)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.total_ensayo_s:02d} s')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        
        btn_stop = QtWidgets.QPushButton("Detener Ensayo")
        btn_stop.setStyleSheet("font-size: 14pt; background-color: #c9302c; color: white; padding: 10px;")
        btn_stop.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(btn_stop, 4, 2, 1, 1)

        now = datetime.now()
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{now.strftime('%d-%m-%Y_%H-%M')}_temp.csv"

        self.data_queue = queue.Queue()
        self.comienzo = [True]
        
        self.ser = threading.Thread(
            target=readserial, 
            args=(self.comport, self.baudrate, self.data_queue, self.comienzo, self.csv_filename, 
                  self.total_ensayo_s, self.RPM_ensayo, self.factor_k, self.cero_offset)
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
        while not self.data_queue.empty():
            try: novos = self.data_queue.get_nowait(); nuevos_datos.append(novos)
            except queue.Empty: break

        n = len(nuevos_datos) 
        if n > 0:
            tiempo_actual_ms = nuevos_datos[-1][0]
            t_restante = max(0, int(self.total_ensayo_s - (tiempo_actual_ms / 1000.0)))
            self.countdown_label.setText(f"Tiempo restante: {t_restante:02d} segundos")

            for arr in [self.plot_time, self.plot_carga, self.plot_temp_amb, self.plot_temp_obj, self.plot_vueltas]:
                arr[:] = np.roll(arr, -n)

            for i, d in enumerate(nuevos_datos):
                idx = -n + i  
                self.plot_time[idx], self.plot_temp_amb[idx], self.plot_temp_obj[idx], self.plot_vueltas[idx], self.plot_carga[idx] = d[0]/1000.0, d[1], d[2], d[3], d[4]

            self.data_count += n
            if self.data_count > 40:
                rpm = ((self.plot_vueltas[-1] - self.plot_vueltas[-41]) / (self.plot_time[-1] - self.plot_time[-41])) * 60.0
            else: rpm = 0
            self.plot_velocidad = np.roll(self.plot_velocidad, -n)
            self.plot_velocidad[-n:] = rpm 

            pts = min(self.data_count, self.window_size)
            self.curves[0].setData(self.plot_time[-pts:], self.plot_carga[-pts:])
            self.curves[1].setData(self.plot_time[-pts:], self.plot_temp_amb[-pts:])
            self.curves[2].setData(self.plot_time[-pts:], self.plot_temp_obj[-pts:])
            self.curves[3].setData(self.plot_time[-pts:], self.plot_velocidad[-pts:])

            t_max = self.plot_time[-1]
            t_min = max(0, t_max - self.window_seconds)
            visibles = [self.plot_carga[-pts:], self.plot_temp_amb[-pts:], self.plot_temp_obj[-pts:], self.plot_velocidad[-pts:]]

            for i, gw in enumerate(self.graph_widgets):
                gw.setXRange(t_min, t_max, padding=0)
                y_min, y_max = np.min(visibles[i]), np.max(visibles[i])
                rango = y_max - y_min
                r_min = self.rangos_minimos[i]
                if rango < r_min:
                    centro = (y_max + y_min) / 2.0
                    y_min, y_max, rango = centro - (r_min/2.0), centro + (r_min/2.0), r_min
                
                target_min, target_max = y_min - (rango*0.15), y_max + (rango*0.15)
                self.current_y_maxs[i] += (target_max - self.current_y_maxs[i]) * 0.15 if target_max <= self.current_y_maxs[i] else (target_max - self.current_y_maxs[i])
                self.current_y_mins[i] += (target_min - self.current_y_mins[i]) * 0.15 if target_min >= self.current_y_mins[i] else (target_min - self.current_y_mins[i])
                gw.setYRange(self.current_y_mins[i], self.current_y_maxs[i], padding=0)

    def closeEvent(self, event):
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive(): self.ser.join()
        self.save_data()
        event.accept()

    def save_data(self):
        if os.path.exists(self.csv_filename):
            df = pd.read_csv(self.csv_filename)
            df.to_excel(self.csv_filename.replace('_temp.csv', '.xlsx'), index=False)