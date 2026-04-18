import threading
import time
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QPushButton, QLabel, QSlider, QVBoxLayout, QWidget, QHBoxLayout, QComboBox
from PySide6.QtCore import QTimer


class MockControlPanel(QWidget):
    """Fenêtre de débogage pour contrôler la physique de la voiture."""

    def __init__(self, physics_mock):
        super().__init__()
        self.mock = physics_mock
        self.setWindowTitle("🎮 Contrôle Mock GT3")
        self.resize(320, 350)

        layout = QVBoxLayout()

        # --- NOUVEAU : BOUTON DE CONTACT MANUEL ---
        self.ignition_state = True  # Par défaut, le mock démarre avec le contact allumé
        self.btn_ignition = QPushButton("🔑 Couper le contact")
        self.btn_ignition.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 5px;")
        self.btn_ignition.clicked.connect(self.toggle_ignition)
        layout.addWidget(self.btn_ignition)

        layout.addWidget(QLabel("─" * 40))

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

        # --- BOUTON PILOTE AUTO ---
        self.btn_autopilot = QPushButton("🤖 Lancer Pilote Automatique (Test UI)")
        self.btn_autopilot.setStyleSheet("background-color: #2d5b88; color: white; font-weight: bold; padding: 5px;")
        self.btn_autopilot.clicked.connect(self.run_auto_pilot)
        layout.addWidget(self.btn_autopilot)

        self.setLayout(layout)

    # ==========================================
    # CONTRÔLES MANUELS
    # ==========================================
    def toggle_ignition(self):
        """Alterne l'état du contact et met à jour l'API et l'UI."""
        self.ignition_state = not self.ignition_state

        # Mise à jour sécurisée de l'API
        self.mock.api.update({
            "key_run": self.ignition_state,
            "ignition_on": self.ignition_state
        })

        # Mise à jour visuelle du bouton
        if self.ignition_state:
            self.btn_ignition.setText("🔑 Couper le contact")
            self.btn_ignition.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 5px;")
        else:
            self.btn_ignition.setText("🔑 Mettre le contact")
            self.btn_ignition.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 5px;")

    def update_throttle(self, value):
        self.mock.throttle = float(value)

    def update_brake(self, value):
        self.mock.brake = float(value)

    def update_gear(self, index):
        self.mock.gear = index

    def reset_pedals(self):
        self.slider_throttle.setValue(0)
        self.slider_brake.setValue(0)

    def _restore_button(self):
        """Exécutée par le Main Thread pour réactiver l'UI du Pilote Auto en toute sécurité."""
        self.btn_autopilot.setEnabled(True)
        self.btn_autopilot.setText("🤖 Lancer Pilote Automatique (Test UI)")

        # On s'assure que le bouton de contact reflète l'état final du pilote auto (contact coupé)
        self.ignition_state = False
        self.btn_ignition.setText("🔑 Mettre le contact")
        self.btn_ignition.setStyleSheet("background-color: #5cb85c; color: white; font-weight: bold; padding: 5px;")

    # ==========================================
    # SÉQUENCE DU PILOTE VIRTUEL
    # ==========================================
    def run_auto_pilot(self):
        """Prend le contrôle des inputs du mock physics pour simuler un trajet."""
        self.btn_autopilot.setEnabled(False)
        self.btn_autopilot.setText("🤖 Conduite en cours...")

        def sequence():
            print("\n[MOCK PILOT] 🔑 1. Mise du contact...")
            self.mock.api.update({"key_run": True, "ignition_on": True})
            time.sleep(1.0)

            print("[MOCK PILOT] ⚙️ 2. 1ère vitesse et grosse accélération...")
            self.mock.gear = 1
            self.mock.brake = 0.0
            self.mock.throttle = 70.0
            time.sleep(3.0)

            print("[MOCK PILOT] ⚙️ 3. Passage en 2ème vitesse...")
            self.mock.throttle = 0.0
            time.sleep(0.5)
            self.mock.gear = 2
            self.mock.throttle = 40.0
            time.sleep(4.0)

            print("[MOCK PILOT] 🛣️ 4. Vitesse de croisière...")
            self.mock.throttle = 15.0
            time.sleep(6.0)

            print("[MOCK PILOT] 🛑 5. Freinage progressif...")
            self.mock.throttle = 0.0
            self.mock.brake = 50.0
            time.sleep(3.0)

            print("[MOCK PILOT] 🔑 6. Arrêt complet et coupure du contact...")
            self.mock.brake = 100.0
            self.mock.gear = 0
            time.sleep(1.0)

            self.mock.api.update({"key_run": False, "ignition_on": False})
            self.mock.brake = 0.0

            print("[MOCK PILOT] ✅ Fin du trajet simulé. Vérifiez l'interface QML !")

            # On demande au Main Thread de réactiver l'UI
            QTimer.singleShot(0, self._restore_button)

        threading.Thread(target=sequence, daemon=True).start()