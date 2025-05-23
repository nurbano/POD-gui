from random import randint

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets
import pandas as pd
import configparser
import numpy as np
#import qdarktheme


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ensayo de desgaste")
        self.temperatura= []
        self.velocidad= []
        self.carga= []
        self.cof= []
        self.iter=0

        self.text_var1 = QtWidgets.QLineEdit()
        self.text_var2 = QtWidgets.QLineEdit()
        self.num_var1 = QtWidgets.QSpinBox()
        self.num_var2 = QtWidgets.QSpinBox()
        self.num_var3 = QtWidgets.QSpinBox()
        self.num_var4 = QtWidgets.QSpinBox()
        self.num_var5 = QtWidgets.QSpinBox()
        self.num_var6 = QtWidgets.QSpinBox()

        self.cal_nombre_celda = QtWidgets.QLineEdit()
        self.cal_k = QtWidgets.QSpinBox()
        self.cal_rel_pal = QtWidgets.QSpinBox()
        
        self.show_main()


    def create_ensayar_widget(self):
        self.widget_ensayar = QtWidgets.QWidget()
        self.layout_ensayar = QtWidgets.QGridLayout()
        self.widget_ensayar.setLayout(self.layout_ensayar)
        
                
        self.widget_ensayar.setLayout(self.layout_ensayar)
        self.widget_ensayar.showMaximized()
        # Create subplots
        self.plot_graphs = {}
        titles = ["Carga", "Temperatura", "Velocidad", "CoF"]
        y_labels = ["Carga (Kg)", "Temperatura (°C)", "Velocidad (RPM)", "COF"]
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        self.countdown_label = QtWidgets.QLabel("Tiempo restante: 00:00")
        self.layout_ensayar.addWidget(self.countdown_label, 3, 0, 1, 2)
        self.countdown_timer = QtCore.QTimer()
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.remaining_time = self.num_var1.value()* 60  # assuming num_var1 is duration in minutes
        self.countdown_timer.start()
        for i, (title, y_label, color) in enumerate(zip(titles, y_labels, colors)):
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground("w")
            pen = pg.mkPen(color=color)
            plot_widget.setTitle(title, color="black", size="20pt")
            styles = {"color": "black", "font-size": "14px"}
            plot_widget.setLabel("left", y_label, **styles)
            plot_widget.setLabel("bottom", "Tiempo (Segundos)", **styles)
            #plot_widget.addLegend()
            plot_widget.showGrid(x=True, y=True)
            plot_widget.setYRange(2, 40)
            self.layout_ensayar.addWidget(plot_widget, i // 2, i % 2)
            self.plot_graphs[title] = {
                "widget": plot_widget,
                "time": list(np.linspace(0, 60, 600)),
                #"data": [0],
                "data": [randint(0, 0) for _ in range(600)],
                "line": plot_widget.plot(
                    list(range(600)),
                    #[],
                    [randint(2, 40) for _ in range(600)],
                    name=title.split()[0],
                    pen=pen,
                    symbol="o",
                    symbolSize=4,
                    symbolBrush=color,
                ),
            }

        # Add a timer to simulate new measurements
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_plots)
        self.timer.start()
        # Add a stop button
        self.stop_button = QtWidgets.QPushButton("Detener Ensayo")
        self.layout_ensayar.addWidget(self.stop_button, 2, 0, 1, 2)
        self.stop_button.clicked.connect(self.stop_and_observe)
        
        return self.widget_ensayar
    def update_countdown(self):
        self.remaining_time -= 1
        minutes = self.remaining_time // 60
        seconds = self.remaining_time % 60
        self.countdown_label.setText(f"Tiempo restante: {minutes:02d}:{seconds:02d}")
        if self.remaining_time == 0:
            self.stop_and_observe()
    def create_configurar_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        widget.setLayout(layout)
        layout.addRow("Nombre del Ensayo:", self.text_var1)
        layout.addRow("Duración (min):", self.num_var1)
        layout.addRow("Sentido de giro:", self.text_var2)
        layout.addRow("Temp. Amb.:", self.num_var2)
        layout.addRow("Hum. Amb.:", self.num_var3)
        layout.addRow("Carga (Kg):", self.num_var4)
        layout.addRow("Peso del pin (g):", self.num_var5)
        layout.addRow("Velocidad de Giro (RPM):", self.num_var6)
        self.conf_ok_button = QtWidgets.QPushButton("OK")
        layout.addWidget(self.conf_ok_button)
        
        self.conf_ok_button.clicked.connect(self.save_parameters)

        self.load_parameters()

        return widget

    def load_parameters(self):
        config = configparser.ConfigParser()
        config.read('parameter.ini')
        if 'Parameters' in config:
            self.text_var1.setText(config['Parameters'].get('nombre_ensayo', ''))
            self.num_var1.setValue(config['Parameters'].getint('duracion', 0))
            self.text_var2.setText(config['Parameters'].get('sentido_giro', ''))
            self.num_var2.setValue(config['Parameters'].getint('temp_amb', 0))
            self.num_var3.setValue(config['Parameters'].getint('hum_amb', 0))
            self.num_var4.setValue(config['Parameters'].getint('carga', 0))
            self.num_var5.setValue(config['Parameters'].getint('peso_pin', 0))
            self.num_var6.setValue(config['Parameters'].getint('velocidad_giro', 0))

    def save_parameters(self):
        config = configparser.ConfigParser()
        config['Parameters'] = {
            'nombre_ensayo': self.text_var1.text(),
            'duracion': self.num_var1.value(),
            'sentido_giro': self.text_var2.text(),
            'temp_amb': self.num_var2.value(),
            'hum_amb': self.num_var3.value(),
            'carga': self.num_var4.value(),
            'peso_pin': self.num_var5.value(),
            'velocidad_giro': self.num_var6.value()
        }
        with open('parameter.ini', 'w') as configfile:
            config.write(configfile)
        self.show_main()
      

    def create_calibrar_widget(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout()
        widget.setLayout(layout)


        layout.addRow("Identificación de la Celda de Carga:", self.cal_nombre_celda)
        layout.addRow("Constante de Calibración:", self.cal_k)
        layout.addRow("Relación de Palanca", self.cal_rel_pal)

        self.cal_ok_button = QtWidgets.QPushButton("OK")    
        layout.addWidget(self.cal_ok_button)
        self.cal_ok_button.clicked.connect(self.save_calibration)

        self.load_calibration()

        return widget

    def load_calibration(self):
        config = configparser.ConfigParser()
        config.read('calib.ini')
        if 'Calibration' in config:
            self.cal_nombre_celda.setText(config['Calibration'].get('nombre_celda', ''))
            self.cal_k.setValue(config['Calibration'].getint('k', 0))
            self.cal_rel_pal.setValue(config['Calibration'].getint('rel_pal', 0))

    def save_calibration(self):
        config = configparser.ConfigParser()
        config['Calibration'] = {
            'nombre_celda': self.cal_nombre_celda.text(),
            'k': self.cal_k.value(),
            'rel_pal': self.cal_rel_pal.value()
        }
        with open('calib.ini', 'w') as configfile:
            config.write(configfile)
        self.show_main()


        return config
    def show_main(self):
 # Create a central widget
        #self.setGeometry(100, 100, 300, 200)

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a grid layout
        self.layout = QtWidgets.QGridLayout()
        self.central_widget.setLayout(self.layout)

        # Create buttons
        self.ensayar_button = QtWidgets.QPushButton("Ensayar")
        self.configurar_button = QtWidgets.QPushButton("Configurar")
        self.calibrar_button = QtWidgets.QPushButton("Calibrar")
        self.salida_button = QtWidgets.QPushButton("Salida")

        button_size = QtCore.QSize(200, 100)
        self.ensayar_button.setFixedSize(button_size)
        self.configurar_button.setFixedSize(button_size)
        self.calibrar_button.setFixedSize(button_size)
        self.salida_button.setFixedSize(button_size)

        self.layout.addWidget(self.ensayar_button, 0, 0)
        self.layout.addWidget(self.configurar_button, 0, 1)
        self.layout.addWidget(self.calibrar_button, 1, 0)
        self.layout.addWidget(self.salida_button, 1, 1)

        self.ensayar_button.clicked.connect(self.show_ensayar)
        self.configurar_button.clicked.connect(self.show_configurar)
        self.calibrar_button.clicked.connect(self.show_calibrar)
        self.salida_button.clicked.connect(QtWidgets.QApplication.quit)
        self.showNormal()
        # Create sub-widgets
        
        self.configurar_widget = self.create_configurar_widget()
        self.calibrar_widget = self.create_calibrar_widget()

    def show_ensayar(self):
        self.ensayar_widget = self.create_ensayar_widget()
        print("dar Marcha")
        self.central_widget.layout().removeWidget(self.central_widget)
        self.central_widget = self.widget_ensayar
        self.setCentralWidget(self.central_widget)
        self.showMaximized()

       
        
    def show_configurar(self):
        self.central_widget.layout().removeWidget(self.central_widget)
        self.central_widget = self.configurar_widget
        self.setCentralWidget(self.central_widget)

    def show_calibrar(self):
        self.central_widget.layout().removeWidget(self.central_widget)
        self.central_widget = self.calibrar_widget
        self.setCentralWidget(self.central_widget)

    def update_plots(self):
        for plot in self.plot_graphs.values():
            print(plot["data"])
            plot["time"] = plot["time"][1:]
            plot["time"].append(plot["time"][-1] + 0.1)
            aux = plot["data"][:-1]
            plot["data"]= [randint(2, 40)]
            plot["data"].extend(aux)
            
            plot["line"].setData(plot["time"], plot["data"])
        print("-----------------")

    def save_to_excel(self):
        data = {title: plot["data"] for title, plot in self.plot_graphs.items()}
        df = pd.DataFrame(data)
        df.to_excel(self.text_var1.text()+".xlsx", index=False, startrow=14)

    def stop_and_observe(self):
        self.timer.stop()
        self.countdown_timer.stop()
        print('Ensayo detenido')
        text, ok = QtWidgets.QInputDialog.getText(self, "Observaciones", "Escriba sus observaciones:")
        if ok:
            print(f"Observaciones: {text}")
            self.save_to_excel()
            with pd.ExcelWriter(self.text_var1.text()+".xlsx", mode="a", engine="openpyxl") as writer:
      
                writer.sheets["Sheet1"].cell(row=1, column=1).value = "nombre_ensayo"
                writer.sheets["Sheet1"].cell(row=1, column=2).value = self.text_var1.text()
                writer.sheets["Sheet1"].cell(row=2, column=1).value = "duracion"
                writer.sheets["Sheet1"].cell(row=2, column=2).value = self.num_var1.value()
                writer.sheets["Sheet1"].cell(row=3, column=1).value = "sentido_giro"
                writer.sheets["Sheet1"].cell(row=3, column=2).value = self.text_var2.text()
                
                writer.sheets["Sheet1"].cell(row=4, column=1).value = "temp_amb"
                writer.sheets["Sheet1"].cell(row=4, column=2).value = self.num_var2.value()
                writer.sheets["Sheet1"].cell(row=5, column=1).value = "hum_amb"
                writer.sheets["Sheet1"].cell(row=5, column=2).value = self.num_var3.value()
                writer.sheets["Sheet1"].cell(row=6, column=1).value = "carga"
                writer.sheets["Sheet1"].cell(row=6, column=2).value = self.num_var4.value()
                writer.sheets["Sheet1"].cell(row=7, column=1).value = "peso_pin"
                writer.sheets["Sheet1"].cell(row=7, column=2).value = self.num_var5.value()
                writer.sheets["Sheet1"].cell(row=8, column=1).value = "velocidad_giro"
                writer.sheets["Sheet1"].cell(row=8, column=2).value = self.num_var6.value()
                writer.sheets["Sheet1"].cell(row=9, column=1).value = "Calibración"
                writer.sheets["Sheet1"].cell(row=9, column=2).value = self.cal_nombre_celda.text()
                writer.sheets["Sheet1"].cell(row=10, column=1).value = "Constante de Calibración"
                writer.sheets["Sheet1"].cell(row=10, column=2).value = self.cal_k.value()   
                writer.sheets["Sheet1"].cell(row=11, column=1).value = "Relación de Palanca"
                writer.sheets["Sheet1"].cell(row=11, column=2).value = self.cal_rel_pal.value()
                writer.sheets["Sheet1"].cell(row=12, column=1).value = "Obs."
                writer.sheets["Sheet1"].cell(row=12, column=2).value = text
        self.show_main()

app = QtWidgets.QApplication([])
#qdarktheme.setup_theme()

main = MainWindow()
main.show()
app.exec()