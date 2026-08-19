# CliOS

CliOS est un tableau de bord automobile modulaire en Python, PySide6 et QML,
destiné à un écran tactile ultra-large 1920×720 installé dans l’habitacle.
Il centralise la télémétrie CAN/OBD, les statistiques de trajet, le diagnostic,
le stockage résilient et plusieurs interfaces visuelles.

## Fonctionnalités

- décodage CAN via SocketCAN et définitions JSON par profil véhicule ;
- calculs moteur adaptés au profil actif, notamment puissance, couple disponible
  et charge moteur ;
- statistiques de trajet : distance, consommation, coût, autonomie,
  agressivité, décélération sans accélérateur et accélération longitudinale ;
- diagnostic OBD, monitoring système, stockage USB et export de trajets ;
- quatre styles QML : Apex, Atelier Luxe, GT Modern et Legacy Dashboard ;
- mode simulation avec `--mock`, sans véhicule connecté.

## Architecture en une phrase

Les producteurs publient des `StatePatch` dans [VehicleRuntime](src/runtime.py),
le store conserve des domaines stricts et leurs métadonnées, le bridge Qt expose
uniquement des dictionnaires structurés, puis `UiState.qml` fournit aux styles
des propriétés sémantiques prêtes à afficher.

La description détaillée se trouve dans
[docs/backend_architecture.md](docs/backend_architecture.md), et les règles de
migration dans [docs/migration_runtime.md](docs/migration_runtime.md).

## Organisation du dépôt

```text
main.py                         démarrage et composition des services
src/runtime.py                  passerelle de publication du runtime
src/state_store.py              snapshots, domaines, TTL et qualité
src/signal_catalog.py           catalogue strict des signaux CAN
src/qt_bridge.py                contrat Python/QML structuré
src/services/                  services métier et calculs dérivés
frontend/state/UiState.qml      façade sémantique consommée par les dashboards
frontend/styles/                paquets visuels indépendants
data/can/                       définitions des trames CAN
data/config/                    profils et courbes moteur
tests/                          tests backend, QML et contrats d’architecture
tools/qml_smoke.py              rendu hors écran à 1920×720
```

Le bridge ne fournit volontairement plus les anciennes propriétés plates
`data`, `stats`, `systemHealth` ou `storageStatus`. Toute nouvelle vue doit
passer par `UiState.qml`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Pour l’installation audio Raspberry Pi et la compilation de `pyo`, consulter
[installation/guide_installation_pyo.md](installation/guide_installation_pyo.md).

## Lancement

```bash
# Interface graphique sur véhicule réel
python3 -u main.py --ui gui

# Interface graphique avec simulation
python3 -u main.py --ui gui --mock

# Interface CLI avec simulation
python3 -u main.py --ui cli --mock
```

Options utiles :

```bash
python3 -u main.py --ui gui --mock --log-level DEBUG
python3 -u main.py --ui gui --mock --allow-unsupported-pyside
```

## Validation locale

```bash
python3 -m compileall -q src main.py
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen python3 tools/qml_smoke.py
```

Le smoke test couvre les quatre styles, leurs routes principales et les états
d’avertissement, pause, données absentes et confirmation à 1920×720.

## Données persistantes et stockage

Les profils et sauvegardes sont stockés sous `<clé USB>/clios/`. En l’absence de
clé, CliOS utilise le mode volatile configuré par `StorageManager` ; les
données sont alors perdues au redémarrage. Les trajets sont exportés sous
`trips*/trip_*.json`.

Le service `Export` détecte un fichier `clos_export.json` à la racine d’un
support USB et copie les JSON de trajets avec une signature anti-doublon.

## Contribution

Les règles de contribution et le contrat UI sont décrits dans
[CONTRIBUTING.md](CONTRIBUTING.md). Toute modification du runtime doit ajouter
ou actualiser un test de contrat si elle change un domaine, un signal, une
propriété du bridge ou une façade `UiState`.

## Licence

Projet distribué sous licence GPLv3 (voir [LICENSE](LICENSE)).
