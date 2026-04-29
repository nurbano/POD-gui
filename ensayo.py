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
        # Configuración visual global
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        
        # Cargar archivo de configuración
        self.config = configparser.ConfigParser()
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        ini_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de configuración (.ini)", "", "Archivos INI (*.ini)", options=options
        )
        if ini_path:
            self.config.read(ini_path)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se seleccionó configuración. Saliendo...")
            sys.exit(1)
            
        # Configuración de la ventana principal
        self.setWindowTitle("Tribómetro - Adquisición UTN")
        self.setGeometry(100, 100, 1100, 800)
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.setCentralWidget(self.widget_ensayar)
        
        # Parámetros de Calibración
        self.factor_k = self.config.getfloat('Calibracion', 'factor_de_calibracion', fallback=1.0)
        self.cero_offset = self.config.getfloat('Calibracion', 'cero_offset', fallback=0.0)
        
        self.datos_graficos = [ 
            ("Carga", "Carga", "g"),
            ("Temp. Amb.", "T[ºC]", "b"),
            ("Tempe. Ensayo", "T[ºC]", "y"),
            ("Velocidad", "RPM", "r"), 
        ]
        
        # Parámetros del buffer
        self.window_seconds = 180
        self.window_size = 80 * self.window_seconds 
        self.plot_time = np.zeros(self.window_size)
        self.plot_carga = np.zeros(self.window_size)
        self.plot_temp_amb = np.zeros(self.window_size)
        self.plot_temp_obj = np.zeros(self.window_size)
        self.plot_velocidad = np.zeros(self.window_size)
        self.plot_vueltas = np.zeros(self.window_size)
        self.data_count = 0 
        
        # Rango mínimo de visión (Piso de Zoom) para: [Carga, TempAmb, TempObj, RPM]
        self.rangos_minimos = [2.0, 5.0, 5.0, 20.0] 

        self.curves = []
        self.graph_widgets = []

        # Creación de los gráficos optimizados
        for i, (title, y_label, color) in enumerate(self.datos_graficos):
            gw = pg.PlotWidget()
            gw.setTitle(title, color="black", size="12pt")
            gw.setLabel("left", y_label)
            gw.setLabel("bottom", "Tiempo (s)")
            gw.showGrid(x=True, y=True)
            
            # BLOQUEO DE LAYOUT: Fija el ancho del texto en Y
            gw.getAxis('left').setWidth(80) 
            gw.getViewBox().disableAutoRange()
            
            # OPTIMIZACIÓN DE RUIDO: Línea fina y downsample tipo 'peak'
            curve = gw.plot(
                [], [], 
                pen=pg.mkPen(color, width=1), 
                clipToView=True, 
                autoDownsample=True, 
                downsampleMethod='peak'
            )
            
            self.curves.append(curve)
            self.graph_widgets.append(gw)
            
            if i == 0:
                self.layout_ensayar.addWidget(gw, 0, 0, 1, 3) 
            else:
                self.layout_ensayar.addWidget(gw, 1, i - 1, 1, 1) 

        # Temporizador de pantalla a 5 FPS (200ms)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200) 
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        
        # Variables de ensayo
        self.total_ensayo_s = self.config.getint('Ensayo', 't_ensayo', fallback=60)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        
        # Etiqueta Hardware Timing
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.total_ensayo_s:02d} s')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #222;")
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        
        self.stop_button = QtWidgets.QPushButton("Detener Ensayo")
        self.stop_button.setStyleSheet("background-color: #c9302c; color: white; padding: 10px; font-size: 14pt;")
        self.stop_button.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(self.stop_button, 4, 2, 1, 1)

        now = datetime.now()
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{now.strftime('%d-%m-%Y_%H-%M')}_temp.csv"

        # Hilo Serie
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
            try: nuevos_datos.append(self.data_queue.get_nowait())
            except queue.Empty: break

        n = len(nuevos_datos) 
        if n > 0:
            tiempo_actual_ms = nuevos_datos[-1][0]
            t_rest = max(0, int(self.total_ensayo_s - (tiempo_actual_ms / 1000.0)))
            self.countdown_label.setText(f"Tiempo restante: {t_rest:02d} segundos")

            self.plot_time = np.roll(self.plot_time, -n)
            self.plot_carga = np.roll(self.plot_carga, -n)
            self.plot_temp_amb = np.roll(self.plot_temp_amb, -n)
            self.plot_temp_obj = np.roll(self.plot_temp_obj, -n)
            self.plot_vueltas = np.roll(self.plot_vueltas, -n)

            for i, d in enumerate(nuevos_datos):
                idx = -n + i  
                self.plot_time[idx], self.plot_temp_amb[idx], self.plot_temp_obj[idx], self.plot_vueltas[idx], self.plot_carga[idx] = d[0]/1000.0, d[1], d[2], d[3], d[4]

            self.data_count += n
            
            if self.data_count > 40:
                dt = self.plot_time[-1] - self.plot_time[-41]
                dv = self.plot_vueltas[-1] - self.plot_vueltas[-41]
                rpm = (dv / dt) * 60.0 if dt > 0 else 0
            else: 
                rpm = 0
                
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

            # --- LA CLAVE DEL RENDIMIENTO: Histéresis Matemática ---
            for i, gw in enumerate(self.graph_widgets):
                gw.setXRange(t_min, t_max, padding=0)
                
                y_min, y_max = np.min(visibles[i]), np.max(visibles[i])
                rango = y_max - y_min
                r_min = self.rangos_minimos[i]
                
                # Regla de Piso de Zoom (Evita que el ruido se amplifique al infinito)
                if rango < r_min:
                    centro = (y_max + y_min) / 2.0
                    y_min = centro - (r_min / 2.0)
                    y_max = centro + (r_min / 2.0)

                # Leemos la escala actual que está dibujada en la pantalla
                pantalla_actual = gw.viewRange()[1] 
                p_min, p_max = pantalla_actual[0], pantalla_actual[1]

                # HISTÉRESIS: Solo recalcular si la señal rompe el techo/piso, 
                # o si la pantalla quedó gigante y la señal es un puntito microscópico.
                if y_min < p_min or y_max > p_max or (p_max - p_min) > (y_max - y_min) * 3:
                    margen = (y_max - y_min) * 0.15
                    gw.setYRange(y_min - margen, y_max + margen, padding=0)

    def closeEvent(self, event):
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive(): self.ser.join()
        self.save_data()
        event.accept()

    def save_data(self):
        if os.path.exists(self.csv_filename):
            print("Exportando a Excel...")
            df = pd.read_csv(self.csv_filename)
            df.to_excel(self.csv_filename.replace('_temp.csv', '.xlsx'), index=False)
            print(f"✅ Archivo final guardado exitosamente.")
            
        try:
            txt_path = self.csv_filename.replace('_temp.csv', '.txt')
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"REPORTE DE ENSAYO - {self.nombre_estacion}\n")
                f.write(f"Finalizado el: {datetime.now()}\n\nConfiguración:\n")
                for sec in self.config.sections():
                    f.write(f"[{sec}]\n")
                    for k, v in self.config.items(sec):
                        f.write(f"{k} = {v}\n")
                    f.write("\n")
        except Exception as e:
            print(f"Error al generar TXT: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    sys.exit(app.exec_())