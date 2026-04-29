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
        
        # 1. Cargar archivo de configuración .ini
        self.config = configparser.ConfigParser()
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.ReadOnly
        ini_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de configuración (.ini)", "", "Archivos INI (*.ini);;Todos los archivos (*)", options=options
        )
        if ini_path:
            self.config.read(ini_path)
        else:
            QtWidgets.QMessageBox.critical(self, "Error", "No se seleccionó configuración. Saliendo...")
            sys.exit(1)
            
        # 2. Configuración de la ventana
        self.setWindowTitle("Tribómetro - Adquisición de Alta Performance")
        self.setGeometry(100, 100, 1100, 800)
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
        
        # === CONFIGURACIÓN DE BUFFERS (Ventana Deslizante) ===
        self.window_seconds = 180  # 3 minutos de historial visible
        self.sps = 80              # Samples per second (aprox)
        self.window_size = self.sps * self.window_seconds 
        
        self.plot_time = np.zeros(self.window_size)
        self.plot_carga = np.zeros(self.window_size)
        self.plot_temp_amb = np.zeros(self.window_size)
        self.plot_temp_obj = np.zeros(self.window_size)
        self.plot_velocidad = np.zeros(self.window_size)
        self.plot_vueltas = np.zeros(self.window_size)
        self.data_count = 0 
        
        self.curves = []
        self.graph_widgets = []
        
        # Variables para el Suavizado de la Escala (Easing)
        self.current_y_mins = [0.0] * 4
        self.current_y_maxs = [1000.0, 40.0, 80.0, 1000.0]

        # 3. Creación de los gráficos
        for i, (title, y_label, color, min_val, max_val) in enumerate(self.datos_graficos):
            graphWidget = pg.PlotWidget()
            graphWidget.setTitle(title, color="black", size="12pt")
            graphWidget.setLabel("left", y_label)
            graphWidget.setLabel("bottom", "Tiempo (s)")
            graphWidget.showGrid(x=True, y=True)

            # Fija el ancho del texto del eje para evitar tirones
            graphWidget.getAxis('left').setWidth(70) 
            graphWidget.getViewBox().disableAutoRange()

            # AGREGADO: subsample evita dibujar líneas infinitas que matan el procesador
            curve = graphWidget.plot(
                [], [], 
                pen=pg.mkPen(color, width=2), 
                clipToView=True,
                autoDownsample=True,
                downsampleMethod='subsample'
            )
            
            self.curves.append(curve)
            self.graph_widgets.append(graphWidget)
            
            if i == 0:
                self.layout_ensayar.addWidget(graphWidget, 0, 0, 1, 3) 
            else:
                self.layout_ensayar.addWidget(graphWidget, 1, i - 1, 1, 1) 

        # 4. Temporizador de Interfaz (5 FPS para estabilidad)
        self.timer = QtCore.QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()
        
        # Parámetros del ensayo
        self.total_ensayo_s = self.config.getint('Ensayo', 't_ensayo', fallback=60)
        self.comport = self.config.get('Serial', 'comport', fallback='COM4')
        self.baudrate = self.config.getint('Serial', 'baudrate', fallback=115200)
        self.RPM_ensayo = self.config.getint('Ensayo', 'RPM_ensayo', fallback=800)
        self.nombre_ensayo = self.config.get('Ensayo', 'nombre_ensayo', fallback='Ensayo')
        self.nombre_estacion = self.config.get('Ensayo', 'nombre_estacion', fallback='Estación 1')
        
        self.countdown_label = QtWidgets.QLabel(f'Tiempo restante: {self.total_ensayo_s:02d} segundos')
        self.countdown_label.setAlignment(QtCore.Qt.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #222;")
        self.layout_ensayar.addWidget(self.countdown_label, 4, 0, 1, 2)
        
        self.stop_button = QtWidgets.QPushButton("Detener Ensayo")
        self.stop_button.setStyleSheet("font-size: 14pt; background-color: #c9302c; color: white; padding: 10px;")
        self.stop_button.clicked.connect(self.parar_ensayo)
        self.layout_ensayar.addWidget(self.stop_button, 4, 2, 1, 1)

        now = datetime.now()
        fecha_hora = now.strftime("%d-%m-%Y_%H-%M")
        self.csv_filename = f"./{self.nombre_estacion}_{self.nombre_ensayo}_{fecha_hora}_temp.csv"

        # 5. Hilo de Adquisición
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
        while not self.data_queue.empty():
            try:
                nuevos_datos.append(self.data_queue.get_nowait())
            except queue.Empty:
                break

        n = len(nuevos_datos) 
        
        if n > 0:
            tiempo_actual_ms = nuevos_datos[-1][0]
            t_restante = max(0, int(self.total_ensayo_s - (tiempo_actual_ms / 1000.0)))
            self.countdown_label.setText(f"Tiempo restante: {t_restante:02d} segundos")

            self.plot_time = np.roll(self.plot_time, -n)
            self.plot_carga = np.roll(self.plot_carga, -n)
            self.plot_temp_amb = np.roll(self.plot_temp_amb, -n)
            self.plot_temp_obj = np.roll(self.plot_temp_obj, -n)
            self.plot_vueltas = np.roll(self.plot_vueltas, -n)

            for i, datos in enumerate(nuevos_datos):
                t_ms, t_amb, t_obj, vte, crg = datos
                idx = -n + i  
                self.plot_time[idx] = t_ms / 1000.0
                self.plot_carga[idx] = crg
                self.plot_temp_amb[idx] = t_amb
                self.plot_temp_obj[idx] = t_obj
                self.plot_vueltas[idx] = vte

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

            # === ESCALADO ASIMÉTRICO DEL EJE Y (La solución al tildazo) ===
            t_max = self.plot_time[-1]
            t_min = max(0, t_max - self.window_seconds)
            
            visibles = [
                self.plot_carga[-pts:],
                self.plot_temp_amb[-pts:],
                self.plot_temp_obj[-pts:],
                self.plot_velocidad[-pts:]
            ]

            for i, gw in enumerate(self.graph_widgets):
                gw.setXRange(t_min, t_max, padding=0)
                
                y_min, y_max = np.min(visibles[i]), np.max(visibles[i])
                rango = y_max - y_min
                margen = rango * 0.15 if rango > 0 else 5.0 
                
                target_min = y_min - margen
                target_max = y_max + margen

                # ZOOM OUT Instantáneo: Si el pico es grande, salta directo para no ocultarlo
                if target_max > self.current_y_maxs[i]:
                    self.current_y_maxs[i] = target_max
                else:
                    # ZOOM IN Suavizado: Si el pico desaparece, baja en cámara lenta (15% por iteración)
                    self.current_y_maxs[i] += (target_max - self.current_y_maxs[i]) * 0.15
                    
                if target_min < self.current_y_mins[i]:
                    self.current_y_mins[i] = target_min
                else:
                    self.current_y_mins[i] += (target_min - self.current_y_mins[i]) * 0.15
                    
                gw.setYRange(self.current_y_mins[i], self.current_y_maxs[i], padding=0)

    def closeEvent(self, event):
        self.comienzo[0] = False
        if hasattr(self, 'ser') and self.ser.is_alive():
            self.ser.join()
        self.save_data()
        event.accept()

    def save_data(self):
        try:
            if os.path.exists(self.csv_filename):
                print("Exportando a Excel...")
                df = pd.read_csv(self.csv_filename)
                excel_path = self.csv_filename.replace('_temp.csv', '.xlsx')
                df.to_excel(excel_path, index=False)
                print(f"✅ Excel generado: {excel_path}")
        except Exception as e:
            print(f"❌ Error en exportación: {e}")

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