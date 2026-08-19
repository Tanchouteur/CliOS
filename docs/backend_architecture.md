# Architecture des données runtime

## Flux de référence

```text
CAN / simulation / matériel
        │
        ▼
Décodage et validation des signaux
        │
        ▼
VehicleStateStore (valeur, domaine, source, unité, fraîcheur)
        │
        ├──► services dérivés (PowertrainMetrics, Dynamics, TripStats)
        │
        ▼
DashboardBridge
        │
        ▼
UiState.qml puis dashboards
```

Le store est la source de vérité des données runtime. `VehicleAPI` en est la
façade de publication et de lecture. Un producteur publie avec une `source`, et
avec un `ttl_s` lorsque sa donnée peut devenir périmée.

## Contrat par domaines

Les dictionnaires sont séparés par responsabilité métier, pas par service :

- `vehicleState.powertrain`
- `vehicleState.motion`
- `vehicleState.wheels`
- `vehicleState.body`
- `vehicleState.assistance`
- `vehicleState.dynamics`
- `vehicleState.environment`
- `tripState`
- `diagnosticsState`
- `systemState`
- `sessionState`
- `dataQuality`

Plusieurs services peuvent enrichir un même domaine. Le frontend ne dépend donc
pas du nom, du découpage interne ou du remplacement futur d'un service.

## Publication

Préférer une publication explicite :

```python
api.update_domain(
    "powertrain",
    {"estimated_power_kw": 42.0},
    source="powertrain-metrics",
    ttl_s=0.25,
)
```

`api.update(values, source="...")` reste adapté aux lots contenant plusieurs
domaines : les clés sont alors classées par `infer_domain`.

Chaque nouveau signal doit avoir :

1. un nom sans ambiguïté physique ;
2. un domaine stable ;
3. une unité dans `state_store.py` si la valeur est mesurée ;
4. une source ;
5. un TTL si le maintien d'une ancienne valeur peut tromper l'interface.

## Compatibilité

`bridge.data` et `bridge.stats` sont maintenus comme vues plates pendant la
migration des anciens styles. Le nouveau code QML doit utiliser les propriétés
structurées. `UiState.qml` fusionne actuellement les deux contrats afin que tous
les styles puissent migrer progressivement.

Les alias `coasting_km` et `g_force` sont également transitoires. Les noms de
référence sont `deceleration_without_throttle_km` et `longitudinal_g`.

L'animation de démarrage est une donnée de présentation séparée : elle ne doit
jamais être lue par TripStats, Dynamics ou un autre calcul backend.
