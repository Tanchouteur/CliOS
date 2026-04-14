from PySide6.QtGui import Qt
from PySide6.QtWidgets import QPushButton, QLabel, QSlider, QVBoxLayout, QWidget, QHBoxLayout, QComboBox
import threading
import time
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QPushButton, QLabel, QSlider, QVBoxLayout, QWidget, QHBoxLayout, QComboBox


class MockControlPanel(QWidget):
    """Fenêtre de débogage pour contrôler la physique de la voiture."""

    def __init__(self, physics_mock):
        super().__init__()
        self.mock = physics_mock
        self.setWindowTitle("🎮 Contrôle Mock GT3")
        self.resize(320, 300)

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

        # --- LIGNE DE SÉPARATION VISUELLE ---
        layout.addWidget(QLabel("─" * 40))

        # --- NOUVEAU : BOUTON PILOTE AUTO ---
        self.btn_autopilot = QPushButton("🤖 Lancer Pilote Automatique (Test UI)")
        self.btn_autopilot.setStyleSheet("background-color: #2d5b88; color: white; font-weight: bold; padding: 5px;")
        self.btn_autopilot.clicked.connect(self.run_auto_pilot)
        layout.addWidget(self.btn_autopilot)

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

    # ==========================================
    # SÉQUENCE DU PILOTE VIRTUEL
    # ==========================================
    def run_auto_pilot(self):
        """Prend le contrôle des inputs du mock physics pour simuler un trajet."""

        # On désactive le bouton pour éviter de lancer 2 pilotes en même temps
        self.btn_autopilot.setEnabled(False)
        self.btn_autopilot.setText("🤖 Conduite en cours...")

        def sequence():
            print("\n[MOCK PILOT] 🔑 1. Mise du contact...")
            self.mock.api.update({"key_run": True})
            time.sleep(1.0)

            print("[MOCK PILOT] ⚙️ 2. 1ère vitesse et grosse accélération...")
            self.mock.gear = 1
            self.mock.brake = 0.0
            self.mock.throttle = 70.0
            time.sleep(3.0)

            print("[MOCK PILOT] ⚙️ 3. Passage en 2ème vitesse...")
            self.mock.throttle = 0.0
            time.sleep(0.5)  # Petit temps mort pour simuler l'embrayage
            self.mock.gear = 2
            self.mock.throttle = 40.0
            time.sleep(4.0)

            print("[MOCK PILOT] 🛣️ 4. Vitesse de croisière...")
            self.mock.throttle = 15.0  # Maintien de la vitesse
            time.sleep(6.0)

            print("[MOCK PILOT] 🛑 5. Freinage progressif...")
            self.mock.throttle = 0.0
            self.mock.brake = 50.0
            time.sleep(3.0)

            print("[MOCK PILOT] 🔑 6. Arrêt complet et coupure du contact...")
            self.mock.brake = 100.0
            self.mock.gear = 0
            time.sleep(1.0)

            # C'est ÇA qui va déclencher l'animation "PAUSED" dans ton QML !
            self.mock.api.update({"key_run": False})
            self.mock.brake = 0.0

            print("[MOCK PILOT] ✅ Fin du trajet simulé. Vérifiez l'interface QML !")

            # On réactive le bouton pour le prochain test
            self.btn_autopilot.setEnabled(True)
            self.btn_autopilot.setText("🤖 Lancer Pilote Automatique (Test UI)")

        # On lance la séquence dans un thread pour que la fenêtre PyQt ne freeze pas
        threading.Thread(target=sequence, daemon=True).start()