# 🎨 Architecture des Thèmes & Pages de Dashboards CliOS

Chaque style de tableau de bord est complètement indépendant et réside dans son propre sous-dossier :

```text
frontend/
├── shared_pages/              <-- Pages de configuration système communes et neutres
│   ├── AppearancePage.qml     (Thèmes, Roue chromatique & Ambiance LED)
│   ├── VehiclePage.qml        (Profils véhicule, Révision & Boîte de vitesses)
│   ├── ServicesPage.qml       (Interrupteurs & Réglages des services en direct)
│   ├── SystemPage.qml         (CPU/RAM, Réseau, Mode SD, Logs, Diagnostic, Actions)
│   ├── DeveloperPage.qml      (Moniteur des trames CAN brutes en direct)
│   ├── DiagnosticPage.qml     (Scan ECU et lecture des codes défauts DTC)
│   └── components/            (Primitives partagées : Button, Card, PageHeader, etc.)
│
└── styles/                    <-- Dossiers de chaque Dashboard
    ├── gt_modern/             (Cockpit typé GT avec pages de conduite dédiées)
    ├── apex/                  (Affichage dynamique 3D néon)
    ├── atelier_luxe/          (Chronomètres d'orfèvrerie & tiroir de contrôle)
    ├── legacy_dashboard/      (Interface historique)
    └── _template/             (Gabarit pour créer un nouveau thème)
```

---

## 🧭 Pages et Vues Requises

Un tableau de bord CliOS est libre dans son design (cadrans ronds, barres néon, chronos, affichage minimaliste), mais doit permettre au conducteur d'accéder aux fonctionnalités du véhicule et du système.

### 1. Vues Principales de Conduite (Propres à chaque Dashboard)
Chaque style implémente ses propres écrans de conduite dans son dossier (ex: `pages/GtDrivePage.qml`, `pages/ApexDrive.qml`) :
* **Vue Conduite (Drive)** : Vitesse, Régime moteur (RPM), Rapport engagé, Jauges critiques (Essence, Température Eau/Huile), Voyants d'alerte.
* **Vue Trajet (Trip / Stats)** : Compteurs kilométriques A & B, consommations moyennes, autonomie restante, chrono de session.
* **Vue Performance / Télémétrie (Optionnelle)** : Pressions, boost turbo, accélérations G-force, temps au tour.

### 2. Pages de Réglages & Système (Pages Communes)
Pour éviter de redévelopper l'ensemble des écrans techniques dans chaque thème, CliOS fournit le dossier `frontend/shared_pages/` :

| Page partagée | Rôle | Composants & Données |
| :--- | :--- | :--- |
| **`AppearancePage.qml`** | Personnalisation visuelle | Sélecteur de style graphique, roue chromatique HSV et presets couleur d'accentuation / LEDs. |
| **`VehiclePage.qml`** | Gestion du véhicule | Sélection / création de profils de voiture, suivi révision et étalonnage des rapports de boîte. |
| **`ServicesPage.qml`** | Supervision des modules | Interrupteurs ON/OFF et réglages en direct de chaque service (CAN, Bluetooth, Audio, etc.). |
| **`SystemPage.qml`** | Santé & Maintenance | Surveillance CPU/RAM, stockage USB, mode SD OverlayFS, logs en direct, diagnostic, reboot et arrêt. |
| **`DiagnosticPage.qml`** | Diagnostic moteur | Déclenchement d'un scan OBD2 ISO-TP et affichage des codes défauts DTC enregistrés. |
| **`DeveloperPage.qml`** | Analyse technique | Grille de tous les signaux CAN normalisés en direct avec qualité de transmission. |

---

## 🔌 Comment intégrer les Pages Communes dans un Dashboard ?

Deux approches sont possibles selon le niveau de personnalisation souhaité :

### Approche 1 : Navigation vers les pages partagées (Recommandée)
C'est l'approche utilisée par **`gt_modern`** et **`apex`**. Votre `Dashboard.qml` charge les pages partagées directement dans son `Loader` de sous-pages :

```qml
// Dans frontend/styles/mon_style/Dashboard.qml
var routes = {
    appearance: "../../shared_pages/AppearancePage.qml",
    vehicle:    "../../shared_pages/VehiclePage.qml",
    services:   "../../shared_pages/ServicesPage.qml",
    system:     "../../shared_pages/SystemPage.qml",
    diagnostic: "../../shared_pages/DiagnosticPage.qml",
    developer:  "../../shared_pages/DeveloperPage.qml"
}

function openPage(pageId) {
    subPageLoader.source = Qt.resolvedUrl(routes[pageId])
}
```
* **Avantage :** Les pages s'adaptent automatiquement aux couleurs de votre thème (`palette` définie dans votre `style.json`) via `StyleManager`, sans aucun code redondant.

---

### Approche 2 : Interface de Réglages 100 % sur-mesure
C'est l'approche utilisée par **`atelier_luxe`** (avec son `LuxeControlDrawer.qml`). Vous pouvez concevoir vos propres panneaux de réglages dans le style de votre dashboard, en appelant directement les méthodes du `bridge` et les états de `UiState` :

```qml
import "../../state" as S

// Lire une donnée système :
Text { text: S.UiState.systemVersion }

// Déclencher une action système :
MouseArea {
    onClicked: {
        bridge.restartApplication()     // Redémarrer CliOS
        // bridge.shutdownSystem()      // Éteindre le Raspberry Pi
        // bridge.rebootSystem()        // Reboot matériel
        // bridge.save_setting("theme.main", "#FF5500") // Sauvegarder la couleur
        // bridge.toggleService("Leds", true)           // Activer un service
    }
}
```

---

## 📝 Structure du Manifeste (`style.json`)

Chaque style doit obligatoirement posséder un `style.json` :

```json
{
    "id": "mon_style",
    "label": "Mon Style Course",
    "description": "Tableau de bord sport haute lisibilité",
    "order": 10,
    "dashboard": "Dashboard.qml",
    "palette": {
        "background": "#05080E",
        "surface": "#0C121D",
        "surfaceRaised": "#141D2C",
        "surfaceSoft": "#1B263B",
        "text": "#F1F5F9",
        "textSecondary": "#8B9BB4",
        "outline": "#23334D",
        "gaugeTrack": "#162234"
    },
    "metrics": {
        "radiusSmall": 8,
        "radiusMedium": 14,
        "radiusLarge": 22,
        "borderWidth": 1.5
    }
}
```

---

## ⚡ Créer un Nouveau Style en 1 Commande

Utilisez le générateur automatique de template :

```bash
python3 tools/create_ui_style.py racing_red "Racing Red"
```

Il crée un nouveau dossier prêt à l'emploi dans `frontend/styles/racing_red/` avec son manifeste valide et son point d'entrée `Dashboard.qml`.

---

## 🧪 Validation et Tests Graphiques

Pour valider qu'un style se charge sans aucune erreur de syntaxe ou d'import :

```bash
# Vérification de la conformité structurelle
python3 -m unittest tests.test_ui_structure -v

# Rendu visuel complet des 15 vues à 1920x720 (Smoke Test)
python3 tools/qml_smoke.py
```
