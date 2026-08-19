# Architecture des données runtime

## Flux de référence

```text
CAN / simulation / matériel
        │
        ▼
Décodage + catalogue strict des signaux
        │
        ▼
VehicleRuntime → VehicleStateStore
        │          (snapshots atomiques, source, unité, TTL, qualité)
        ├──► services dérivés (VehicleMetrics, Dynamics, TripStats)
        │
        ▼
DashboardBridge (contrat structuré uniquement)
        │
        ▼
UiState.qml (façade sémantique) → dashboards
```

`VehicleStateStore` est l'unique source de vérité runtime. Un producteur ne
peut publier qu'avec un domaine explicite, une source et, pour une mesure
vivante, un TTL. Il n'existe plus de vue plate ni de domaine `misc`.

## Domaines

Les domaines décrivent le véhicule, pas l'organisation des services :

- `powertrain`, `motion`, `wheels`, `body`, `assistance`, `dynamics`,
  `environment`, `controls`, `alerts` dans `vehicleState` ;
- `tripState`, `diagnosticsState`, `sessionState`, `calibrationState` ;
- `systemState` pour la version, la télémétrie, la santé des services et le
  stockage ;
- `presentationState` pour les animations qui ne doivent jamais alimenter les
  calculs ;
- `dataQuality` pour la source, l'unité, l'âge, le TTL et la qualité.

Plusieurs services peuvent enrichir un domaine. Le frontend ne dépend donc pas
du nom du service producteur.

## Publication et lecture

```python
runtime.publish(
    "powertrain",
    {"estimated_power_kw": 42.0},
    source="vehicle-metrics",
    ttl_s=0.25,
    units={"estimated_power_kw": "kW"},
)

snapshot = runtime.snapshot()
rpm = snapshot.domain("powertrain").get("rpm", 0.0)
```

Pour une mise à jour cohérente de plusieurs domaines, utiliser
`runtime.publish_many()` avec plusieurs `StatePatch`. Les snapshots sont des
copies cohérentes : un calcul ne lit jamais un dictionnaire partagé en cours de
mutation.

Tous les signaux produits par le décodeur CAN doivent être déclarés dans
`src/signal_catalog.py`. Une clé absente fait échouer le décodage de manière
visible au lieu d'être silencieusement rangée dans un fourre-tout.

## Frontend

`DashboardBridge` n'expose que les propriétés structurées. Les quatre styles
livrés lisent leurs valeurs d'affichage via les propriétés sémantiques de
`UiState.qml`. Les pages développeur peuvent explorer les domaines et leur
métadonnée, sans reconstruire une carte plate.

Les anciens contrats `bridge.data`, `bridge.stats`, `bridge.systemHealth` et
`bridge.storageStatus` ont été supprimés. Les alias `coasting_km` et `g_force`
n'existent plus ; les noms physiques sont
`deceleration_without_throttle_km` et `longitudinal_g`.

## Fréquences et responsabilités

- lecture et intégration TripStats : 50 Hz ;
- publication TripStats et calculs dérivés : 20 Hz ;
- projection rapide du bridge : 60 Hz, avec émission seulement si la révision
  concernée a changé ;
- santé système et qualité : 1 Hz.

La fin de trajet est atomique : `TripSessionManager` passe en `ENDING`, capture
les statistiques finales, ferme l'accumulateur et publie un nouvel état vide.
Une itération déjà en vol ne peut pas réinjecter de distance après la clôture.

Les tests de contrat vérifient le catalogue CAN, la surface publique du bridge
et l'absence des anciens accès QML.
