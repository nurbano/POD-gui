# POD-gui
Pin on Disk Graphical user interface

## Objetivos
- Crear una interfaz gráfica para automatizar los ensayos de la máquina Pin On Disk del LEDFS.

## Descripción del Ensayo:

1. Obtener el valor de precargar
2. Setear velocidad (frecuencia). 
3. Setear tiempo de esanyo, sentido de giro (horario u antihorario) y carga en KG.
4. Registrar peso de pin, temperatura ambiente y humedad.
5. Registrar nombre del ensayo, fecha y hora.
6. Marcha (comienza el ensayo).
7. Registar valor de celda de carga, temperatura, velocidad de giro y tiempo. Graficar variables preprocesadas en vivo. Mostrar el tiempo faltante del ensayo.
8. Al finalizar el ensayo, ya sea por tiempo o por parada manual, registrar las observaciones del ensayo.
9. Generar un archivo xlsx con todos los datos obtenidos. El mismo contiene un encabezado con todos los datos del ensayo.

## Calibración:
1. Se deberá poder ingresar la relación de palanca, el tipo de celda, y la constante de la celda.

## Descripción del hardware
El hardware se base en un microcontolador arduino uno, el cual registra el valor de la celda de carga a partir de un adquisicor hx711. A su vez se mide la temperatura con un sensor infrarojo conectado a I2C y a partir de interrupciones externas se mide la velocidad de giro con un sensor óptico CNY70.

## Descripción de software
Se desarrolla en python, con una interfaz en pyqt5 y se grafica con pyqtgraph.


