# CliOS

<div align="center">

**Systeme d'exploitation et tableau de bord numerique modulaire pour automobile.**  
*Concu en Python, PySide6, QML et SocketCAN pour les ecrans ultra-larges 1920x720.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Qt / PySide6](https://img.shields.io/badge/PySide6-Qt_6.8%2B-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.qt.io/)
[![Wayland / Cage](https://img.shields.io/badge/Affichage-Cage_Wayland-E95420?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/cage-kiosk/cage)
[![Licence: GPL v3](https://img.shields.io/badge/Licence-GPLv3-blue.svg?style=for-the-badge)](LICENSE)

[Read in English](readme.md) • [Signaler un bug](../../issues) • [Proposer une idee](../../issues)

<br/>

<img src="docs/demos/clios_demo.gif" alt="Demonstration CliOS" width="100%" />

</div>

---

## Fonctionnalites

- **Telemetrie CAN et OBD en direct** : Decodage en continu des trames moteur et chassis via SocketCAN et profils de vehicules JSON.
- **Modele de calcul dynamique** : Calcul en temps reel de la puissance (ch), du couple instantane (Nm), de la charge moteur et des forces G longitudinales.
- **Interfaces modulaires multi-themes (QML)** :
  - **Apex** : Style circuit et sportif a fort contraste avec G-metre et telemetrie avancee.
  - **Atelier Luxe** : Design sobre axe sur le confort de conduite, l'autonomie et les statistiques de trajet.
  - **GT Modern** et **Legacy** : Compteurs classiques et affichages historiques.
- **Analyse de trajets et export USB** : Calcul de la consommation, du cout des trajets, score de conduite et export automatique sur cle USB.
- **DSP Audio et Eclairage d'ambiance** : Synthese sonore dynamique du moteur / filtrage du bruit d'habitacle (`pyo`) et synchronisation de bandeaux LED BLE.
- **Mode simulation sans materiel** : Moteur de simulation physique et CAN interactif pour tester et developper sur macOS, Linux ou Windows sans vehicule.
- **Demarrage rapide Raspberry Pi 5** : Lancement automatique en mode Kiosk Wayland (`cage`) en moins de 5 secondes au contact.

---

## Apercu des themes

<div align="center">

| Apex (Sport et Circuit) | Atelier Luxe (Confort et Tourisme) |
|:---:|:---:|
| <img src="docs/images/apex.jpg" width="480" /> | <img src="docs/images/atelier_luxe.jpg" width="480" /> |
| *Telemetrie haute frequence et Forces G* | *Design moderne et synthese de voyage* |

</div>

---

## Demarrage rapide (Tester sur son PC en 30 secondes)

Aucun materiel ni vehicule n'est requis pour tester ou developper sur CliOS :

```bash
# 1. Cloner le depot
git clone https://github.com/Tanchouteur/ClOS.git
cd ClOS

# 2. Lancer en mode simulation (configure automatiquement le .venv)
./clios --mock
```

> [!TIP]
> Sur les ecrans d'ordinateurs portables, ajustez la taille avec :  
> `QT_SCALE_FACTOR=0.65 ./clios --mock` pour adapter la fenetre 1920x720 a votre ecran.

---

## Installation dans le vehicule (Raspberry Pi et Linux)

CliOS integre un script d'installation interactif automatise :

```bash
git clone https://github.com/Tanchouteur/ClOS.git
cd ClOS
./install.sh
```

L'installateur prend en charge :
- Dependances systeme (`apt`, pilotes audio, `can-utils`, compositeur Wayland `cage`).
- Environnement virtuel `.venv` et compilation de la bibliotheque audio DSP `pyo`.
- Configuration des interfaces CAN (`can-usb`, `slcan`, `candlelight`, `socketcan`).
- Service Systemd Kiosk (`clios.service`) pour demarrage automatique au boot sans bureau lourd.
- Optimisations Fast-Boot optionnelles pour Raspberry Pi 5.

#### Guides d'installation detailles :
- [Guide d'optimisation Fast-Boot Raspberry Pi 5](installation/guide_optimisation_boot_rpi5.md)
- [Guide materiel CAN et regles systeme](installation/guide_fichier_systeme.md)
- [Guide d'installation audio DSP Pyo](installation/guide_installation_pyo.md)

---

## Architecture

CliOS repose sur un flux de donnees unidirectionnel strict :

```text
[ Bus CAN / OBD-II / Mock ]
            │
            ▼
     [ CanService ] ──► (Publication de StatePatch)
            │
            ▼
    [ VehicleRuntime ]
            │
            ▼
     [ StateStore ] ──► (Domaines stricts, TTL & controle qualite)
            │
            ▼
     [ Qt Bridge ] ──► (Pont thread-safe Python / QML)
            │
            ▼
    [ UiState.qml ] ──► (Proprietes semantiques consommees par l'UI)
            │
  ┌─────────┴─────────┐
  ▼                   ▼
[ Theme Apex ]  [ Theme Atelier Luxe ]
```

---

## Contribution

Les contributions sont les bienvenues :
- **Ajout de profils de vehicules** : Definitions JSON / DBC pour d'autres modeles auto (BMW, VAG, Honda, etc.).
- **Creation de themes QML** : Dashboards personnalises, design retro, compteurs numeriques sur-mesure.
- **Nouvelles integrations** : Controle multimedia Spotify/Bluetooth, GPS / OpenStreetMap, support dongle CarPlay/Android Auto.
- **Optimisations logicielles** : Audio DSP, protocoles BLE, temps de boot.

Consultez [CONTRIBUTING.md](CONTRIBUTING.md) pour les regles de developpement et les tests.

---

## Licence

Distribue sous licence **GNU General Public License v3.0** (GPLv3). Voir [LICENSE](LICENSE).
