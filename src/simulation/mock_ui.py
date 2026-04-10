from PySide6.QtGui import Qt
from PySide6.QtWidgets import QPushButton, QLabel, QSlider, QVBoxLayout, QWidget, QHBoxLayout, QComboBox


class MockControlPanel(QWidget):
    """Fenêtre de débogage pour contrôler la physique de la voiture."""

    def __init__(self, physics_mock):
        super().__init__()
        self.mock = physics_mock
        self.setWindowTitle("🎮 Contrôle Mock GT3")
        self.resize(320, 250)

        layout = QVBoxLayout()

        # --- SÉLECTEUR DE BOÎTE DE VITESSES ---
        gear_layout = QHBoxLayout()
        gear_layout.addWidget(QLabel("⚙️ Boîte :"))
        self.gear_combo = QComboBox()
        self.gear_combo.addItems(["N (Neutral)", "1ère", "2ème", "3ème", "4ème", "5ème"])
        self.gear_combo.currentIndexChanged.connect(self.update_gear)
        gear_layout.addWidget(self.gear_combo)
        layout.addLayout(gear_layout)

        # --- PÉDALES ---
        layout.addWidget(QLabel("🟢 Accélérateur (0-100%)"))
        self.slider_throttle = QSlider(Qt.Horizontal)
        self.slider_throttle.setRange(0, 100)
        self.slider_throttle.valueChanged.connect(self.update_throttle)
        layout.addWidget(self.slider_throttle)

        layout.addWidget(QLabel("🔴 Frein (0-100%)"))
        self.slider_brake = QSlider(Qt.Horizontal)
        self.slider_brake.setRange(0, 100)
        self.slider_brake.valueChanged.connect(self.update_brake)
        layout.addWidget(self.slider_brake)

        self.btn_stop = QPushButton("🛑 Relâcher Pédales")
        self.btn_stop.clicked.connect(self.reset_pedals)
        layout.addWidget(self.btn_stop)

        self.setLayout(layout)

    def update_throttle(self, value):
        self.mock.throttle = float(value)

    def update_brake(self, value):
        self.mock.brake = float(value)

    def update_gear(self, index):
        self.mock.gear = index

    def reset_pedals(self):
        self.slider_throttle.setValue(0)
        self.slider_brake.setValue(0)