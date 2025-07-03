import sys

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QFormLayout
)

class Configurator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de archivo .ini")
        self.init_ui()

    def init_ui(self):
        # Variables por defecto
        self.defaults = {
            "factor_de_calibracion": "1.0",
            "cero_offset": "0.0",
            "comport": "COM4",
            "baudrate": "115200",
            "t_ensayo": "1800",
            "RPM_ensayo": "800",
            "nombre_estacion": "POD",
            "nombre_ensayo": "Ensayo_de_prueba"
        }

        form = QFormLayout()

        self.inputs = {}
        for key, value in self.defaults.items():
            self.inputs[key] = QLineEdit(value)
            form.addRow(QLabel(key), self.inputs[key])

        # Botón para elegir ruta y nombre del archivo
        self.file_label = QLabel("Archivo destino: (no seleccionado)")
        self.file_button = QPushButton("Elegir archivo .ini")
        self.file_button.clicked.connect(self.select_file)

        # Botón para guardar
        self.save_button = QPushButton("Guardar .ini")
        self.save_button.clicked.connect(self.save_ini)
        self.save_button.setEnabled(False)

        # Layout principal
        vbox = QVBoxLayout()
        vbox.addLayout(form)
        hbox = QHBoxLayout()
        hbox.addWidget(self.file_button)
        hbox.addWidget(self.file_label)
        vbox.addLayout(hbox)
        vbox.addWidget(self.save_button)
        self.setLayout(vbox)

        self.ini_path = None

    def select_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar como", "", "INI Files (*.ini)")
        if path:
            if not path.endswith('.ini'):
                path += '.ini'
            self.ini_path = path
            self.file_label.setText(f"Archivo destino: {path}")
            self.save_button.setEnabled(True)

    def save_ini(self):
        if not self.ini_path:
            return
        # Construir el contenido del .ini
        content = "[Calibracion]\n"
        content += f"factor_de_calibracion = {self.inputs['factor_de_calibracion'].text()}\n"
        content += f"cero_offset = {self.inputs['cero_offset'].text()}\n"
        content += "[Serial]\n"
        content += f"comport = {self.inputs['comport'].text()}\n"
        content += f"baudrate = {self.inputs['baudrate'].text()}\n"
        content += "[Ensayo]\n"
        content += f"t_ensayo = {self.inputs['t_ensayo'].text()}\n"
        content += f"RPM_ensayo = {self.inputs['RPM_ensayo'].text()}\n"
        content += f"nombre_estacion = {self.inputs['nombre_estacion'].text()}\n"
        content += f"nombre_ensayo = {self.inputs['nombre_ensayo'].text()}\n"

        with open(self.ini_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.save_button.setText("¡Guardado!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Configurator()
    win.show()
    sys.exit(app.exec_())