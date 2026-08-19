# Styles CliOS

Chaque style vit entièrement dans son propre dossier :

```text
frontend/styles/
├── gt_modern/
│   ├── style.json
│   └── Dashboard.qml
└── mon_style/
    ├── style.json
    └── Dashboard.qml
```

## Contrat de données

Les styles sont des paquets de rendu. Ils ne possèdent pas de logique métier et
ne lisent jamais les anciennes cartes plates du bridge. Toute donnée affichée
passe par `frontend/state/UiState.qml` :

```qml
import "../../../state" as S

Text { text: S.UiState.fixed(S.UiState.engineTemp, 0, "—") + " °C" }
```

Pour une donnée absente de la façade, ajouter d’abord une propriété sémantique
dans `UiState.qml`; ne pas contourner le contrat avec `bridge.vehicleState` dans
un composant visuel.

## Ajouter rapidement un style

Le plus rapide est d’utiliser le générateur :

```bash
python3 tools/create_ui_style.py racing_blue "Racing Blue"
```

Il copie le gabarit, renseigne le manifeste et crée `frontend/styles/racing_blue/`. Il reste seulement à modifier ses couleurs ou son `Dashboard.qml`, puis à redémarrer CliOS. Le style apparaît automatiquement dans **Menu → Apparence**.

Il est aussi possible de copier manuellement `_template`, de renommer le dossier puis d’adapter son `id` dans `style.json`.

Le fichier `Dashboard.qml` du gabarit réutilise le cockpit GT. Pour créer une disposition entièrement différente, remplacer son contenu par un composant QML racine `Item`, `Rectangle` ou équivalent.

## Manifeste obligatoire

`style.json` doit contenir :

- un `id` identique au nom du dossier ;
- un `label`, une `description` et un ordre d’affichage `order` ;
- le nom du point d’entrée `dashboard` ;
- les huit couleurs sémantiques de `palette` ;
- facultativement les rayons et l’épaisseur de bordure dans `metrics`.

Les dossiers dont le nom commence par `_` sont ignorés par le catalogue. Un manifeste invalide ou un tableau de bord manquant est également ignoré sans empêcher le démarrage de CliOS.

Le dossier voisin `frontend/style` contient uniquement le moteur interne
(`StyleManager`, thème et paramètres visuels). Les styles à installer ou modifier
vont exclusivement dans `frontend/styles`.

## Tests

Chaque style doit compiler avec la suite QML et rester visible à 1920×720 :

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest tests.test_ui_structure -v
QT_QPA_PLATFORM=offscreen python3 tools/qml_smoke.py
```
