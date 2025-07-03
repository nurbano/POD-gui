import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel
import subprocess

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POD GUI")
        self.init_ui()
        self.resize(640, 480)
    def init_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Laboratorio de Ensayos de Desgaste y Fricción Sólida")
        label.setAlignment(Qt.AlignCenter)
        font = label.font()
        font.setPointSize(18)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        btn_configurar = QPushButton("Configurar")
        btn_visualizar = QPushButton("Visualizar")
        btn_ensayar = QPushButton("Ensayar")
        btn_salir = QPushButton("Salir")

        btn_configurar.clicked.connect(self.abrir_configurar)
        btn_visualizar.clicked.connect(self.abrir_visualizar)
        btn_ensayar.clicked.connect(self.abrir_ensayar)
        btn_salir.clicked.connect(self.close)

        # Hacer que los botones ocupen el 50% del ancho y expandan en alto
        buttons = [btn_configurar, btn_visualizar, btn_ensayar, btn_salir]
        for btn in buttons:
            btn.setSizePolicy(btn.sizePolicy().horizontalPolicy(), btn.sizePolicy().Expanding)
            btn.setMaximumWidth(self.width() // 2)
            btn.setMinimumWidth(self.width() // 2)
            layout.addWidget(btn, stretch=1, alignment=Qt.AlignHCenter)

        # Actualizar el ancho de los botones al cambiar el tamaño de la ventana
        def resizeEvent(event):
            for btn in buttons:
                btn.setMaximumWidth(self.width() // 2)
                btn.setMinimumWidth(self.width() // 2)
                QWidget.resizeEvent(self, event)
        self.resizeEvent = resizeEvent

        self.setLayout(layout)

    def abrir_configurar(self):
        # Aquí puedes llamar a tu programa de configuración
        subprocess.Popen([sys.executable, "configurar.py"])

    def abrir_visualizar(self):
        # Aquí puedes llamar a tu programa de visualización
        #print("Abrir Visualizar")
        subprocess.Popen([sys.executable, "visualizar.py"])

    def abrir_ensayar(self):
        # Aquí puedes llamar a tu programa de ensayo
        subprocess.Popen([sys.executable, "ensayo.py"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())