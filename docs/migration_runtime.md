# Guide de migration vers le runtime structuré

La migration est terminée dans les dashboards fournis. Ce document sert aux
scripts, plugins ou vues externes qui utilisaient encore l’ancien contrat.

## Changements de surface

| Ancien accès | Nouveau contrat |
|---|---|
| `VehicleAPI` dans `src/api.py` | `VehicleRuntime` dans `src/runtime.py` |
| `bridge.data` | `bridge.vehicleState`, puis `UiState.qml` |
| `bridge.stats` | `bridge.tripState`, puis `UiState.qml` |
| `bridge.systemHealth` | `bridge.systemState.health` |
| `bridge.storageStatus` | `bridge.systemState.storage` |
| `bridge.diagnosticCodes` | `bridge.diagnosticsState.codes` |
| `bridge.isScanning` | `bridge.diagnosticsState.scanning` |
| `bridge.hasScanned` | `bridge.diagnosticsState.has_scanned` |
| `session_state` | `sessionState.state` |
| `coasting_km` | `deceleration_without_throttle_km` |
| `g_force` | `longitudinal_g` |

Les anciennes propriétés ne sont plus exposées par compatibilité. Une
intégration externe doit donc être migrée explicitement.

## Publication backend

Ancien style :

```python
api.update({"rpm": rpm, "speed": speed}, source="can")
```

Nouveau style :

```python
from src.state_store import StatePatch

runtime.publish_many((
    StatePatch("powertrain", {"rpm": rpm}, "can", ttl_s=1.5, units={"rpm": "rpm"}),
    StatePatch("motion", {"speed": speed}, "can", ttl_s=1.5, units={"speed": "km/h"}),
))
```

Un dictionnaire ne doit pas mélanger des domaines. Les services dérivés publient
leurs résultats dans le domaine métier correspondant : `VehicleMetrics` enrichit
`powertrain` et `alerts`, `TripStats` enrichit `trip`, `Dynamics` enrichit
`wheels` et `motion`.

## Lecture backend

```python
snapshot = runtime.snapshot()
powertrain = snapshot.domain("powertrain")
motion = snapshot.domain("motion")

rpm = powertrain.get("rpm", 0.0)
speed = motion.get("speed", 0.0)
```

Ne conservez pas une référence vers le dictionnaire d’un service concurrent :
relisez un snapshot pour chaque cycle de calcul. Les métadonnées sont accessibles
avec `runtime.metadata_snapshot()` et indiquent `source`, `unit`, `age_ms`,
`ttl_ms` et `quality` (`VALID` ou `STALE`).

## Lecture QML

Une vue ne doit pas connaître les domaines bruts :

```qml
import "../../../state" as S

Text {
    text: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0") + " km"
}
```

Pour les outils de diagnostic, `S.UiState.debugSignals` fournit une liste
structurée avec `domain`, `key`, `value`, `unit`, `source`, `quality` et `ageMs`.

## Démarche pour une nouvelle donnée

1. Identifier le domaine métier et l’unité physique.
2. Si la donnée vient du CAN, l’ajouter au catalogue strict.
3. Publier avec une source et un TTL cohérent avec sa fréquence.
4. Ajouter une propriété sémantique dans `UiState.qml`.
5. Utiliser cette propriété dans tous les styles concernés.
6. Ajouter un test backend ou de contrat et, si nécessaire, un état au smoke
   test QML.

## Validation

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen python3 tools/qml_smoke.py
```

Le smoke test doit couvrir les quatre styles et terminer par `QML OK`.
