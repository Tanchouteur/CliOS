# 🏎️ CliOS - Smart Automotive Dashboard

![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)
![Qt](https://img.shields.io/badge/UI-QML%20%2F%20PySide6-green.svg)
![License](https://img.shields.io/badge/License-GPLv3-purple.svg)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange.svg)

CliOS est un système embarqué modulaire et léger conçu pour moderniser l'interface des véhicules. Il s'interface directement avec le bus CAN et la prise OBD pour offrir une télémétrie en temps réel, des diagnostics avancés et des fonctionnalités de confort (Active Sound Design, éclairage).

## Aperçu de l'interface QML
![Aperçu de l'interface QML](assets/readme/qml_dashboard.png)

## ✨ État des Fonctionnalités

### ✅ Déployé & Stable
* **Télémétrie CAN & OBD** : Lecture en temps réel et décodage des trames du bus moteur (RPM, Couple, Températures) et interface de debug en direct.
* **Active Sound Design (ASD)** : Synthèse audio réactive (sifflement/aspiration turbo) basée sur la charge ECU et le régime.
* **Gestion Multi-Véhicules** : Profils de voitures avec fichiers de sauvegarde isolés (`save_[id].json`) sélectionnables à chaud.
* **Notifications & Sécurité** : Alertes de conduite (ex: avertissement d'usure si l'embrayage est maintenu enfoncé).
* **Trip Computer Avancé** : Enregistrement de session et estimateur de coût de trajet basé sur la consommation réelle et le prix à la pompe.
* **Acoustique** : Sonomètre intégré mesurant le bruit ambiant (SPL) dans l'habitacle.

### 🚧 En développement
* **Système d'Éclairage (Ambiance)** : Interfaçage avec l'habitacle pour le contrôle des LEDs.
* **Télémétrie Dynamique (IMU)** : Intégration d'une centrale à inertie pour l'affichage des forces G et de l'inclinaison.
* **Monitoring Système** : Suivi en direct de l'empreinte CPU/RAM des micro-services.
* **Mock Provider Avancé** : Simulateur de roulage interactif pour le développement.

### 💡 Roadmap (À venir)
* **Bus Habitacle** : Interfaçage avec le réseau secondaire (Confort, Multimédia, Commandes au volant).
* **Dashcam Télémétrique** : Enregistrement vidéo incrusté des données de conduite.
* **Luminosité Adaptative** : Utilisation du capteur de pluie/luminosité d'origine pour assombrir l'interface QML.
* **Eco-Conduite** : Affichage du coût instantané (€/min) et de l'énergie thermique dissipée lors des freinages.
* **Cloud Sync** : Sauvegarde des historiques de trajets et statistiques globales sur serveur distant.

## Utilisation
1. Cloner le dépôt
2. Installer les dépendances (`pip install -r requirements.txt`)
3. Lancer l'application (`python main.py`)

#### Note
* Vous pouvez avoir des problèmes avec PYO sur windows

## 🏗️ Architecture du Projet

Le système est construit sur une architecture orientée micro-services en Python, couplée à un moteur de rendu graphique QML pour garantir une faible empreinte CPU (idéal pour Raspberry Pi).
```
📂 ClOS
 ┣ 📂 frontend/         # Interface graphique QML (Dashboards, Gauges, Settings)
 ┣ 📂 src/
 ┃ ┣ 📂 services/       # Micro-services autonomes fonctionnant en arrière-plan
 ┃ ┃ ┣ 🐍 can_service.py         # Moteur de lecture CAN
 ┃ ┃ ┣ 🐍 engine_sound_service.py# Synthèse audio dynamique du moteur
 ┃ ┃ ┣ 🐍 diagnostic_service.py  # Scanner OBD et codes défauts
 ┃ ┃ ┣ 🐍 trip_stats_service.py  # Télémétrie et calcul de coût de trajet
 ┃ ┃ ┗ ...
 ┃ ┣ 📂 simulation/     # Outils de Mocking pour le développement hors-véhicule
 ┃ ┃ ┣ 🐍 mock_driver.py         # Générateur de fausses trames réalistes
 ┃ ┃ ┗ 🐍 orchestrator.py        # Gestion dynamique du cycle de vie des services
 ┃ ┗ 📂 tools/          # Utilitaires (Parsers DBC, bridge Qt)
 ┣ 🐍 main.py           # Point d'entrée de l'application
 ┗ 📜 requirements.txt  # Dépendances Python (PySide6, pyo, python-can, etc.)
```

## 🤝 Contribuer au projet

Les Pull Requests sont les bienvenues ! Si tu souhaites ajouter le support d'un nouveau véhicule (nouveau fichier de parsing DBC) ou optimiser l'interface QML :
1. Fork le projet.
2. Crée ta branche de fonctionnalité (`git checkout -b feature/NouvelleJauge`).
3. Commit tes changements (`git commit -m "Ajout d'une jauge de pression turbo"`).
4. Push vers la branche (`git push origin feature/NouvelleJauge`).
5. Ouvre une Pull Request.


## Liste de todo du projet : [TODO.md](TODO.md)
