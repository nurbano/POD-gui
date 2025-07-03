import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets
import numpy as np
import matplotlib.pyplot as plt

app = QtWidgets.QApplication([])
file_dialog = QtWidgets.QFileDialog()
file_dialog.setNameFilter("Excel Files (*.xlsx *.xls)")
file_dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
if file_dialog.exec_():
    file_name = file_dialog.selectedFiles()[0]
    df = pd.read_excel(file_name, sheet_name="Sheet1")
else:
    raise Exception("No file selected.")

#print(df.head())
df.columns = ['timestamp', 'tiempoMs', 'Carga', 'Temp', 'AmbTemp', 'Vueltas']



win = pg.GraphicsLayoutWidget(show=True, title="Variables vs tiempoMs")
win.resize(1000, 600)
win.setWindowTitle('Graficar todas las variables')

variables = ['Carga', 'Temp', 'AmbTemp', 'Vueltas']

y= df['Vueltas']
x= df['tiempoMs']/1000

rpm= np.zeros_like(y)
rpm_moving_average = np.zeros_like(y)
for i in range(20, len(y)):
    rpm[i]= (y[i] - y[i-20]) / (x[i] - x[i-20])*60
       # Calcular RPM como la derivada instantánea
    rpm_moving_average[i] = np.mean(rpm[i-20:i])  # Calcular el promedio móvil de las RPM
df['RPM'] = rpm_moving_average
variables = ['Carga', 'Temp', 'AmbTemp', 'RPM']

# Convertir tiempoMs a segundos para el eje x
df['tiempo_s'] = df['tiempoMs'] / 1000

for i, var in enumerate(variables):
    p = win.addPlot(row=i, col=0, title=f"{var} vs tiempo (s)")
    colors = {'Carga': 'r', 'Temp': 'g', 'AmbTemp': 'b', 'RPM': 'm'}

    if var == 'Carga':
        # Carga ocupa la mitad superior, todo el ancho
        p.setGeometry(0, 0, win.width(), win.height() // 2)
        p.plot(df['tiempo_s'], df[var], pen=colors[var])
    else:
        # Las otras variables ocupan la mitad inferior, repartidas en el ancho
        col_idx = variables[1:].index(var)
        p.setGeometry(
            col_idx * win.width() // 3, 
            win.height() // 2, 
            win.width() // 3, 
            win.height() // 2
        )
        p.plot(df['tiempo_s'], df[var], pen=colors[var])
    p.setLabel('left', var)
    p.setLabel('bottom', 'tiempo (s)')

if __name__ == '__main__':
    QtWidgets.QApplication.instance().exec_()