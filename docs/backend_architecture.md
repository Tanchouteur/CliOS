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
DashboardBridge (contrat structuré et commandes AppShell)
        │
        ▼
UiState.qml → AppShell → dashboards Theme API v1
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

## Responsabilités des services

| Service | Entrées principales | Domaines publiés | Cadence |
|---|---|---|---|
| `CAN_Moteur` | trames SocketCAN + catalogue DBC | domaines CAN, `system.can_decode_errors` | selon les trames |
| `VehicleMetrics` | `powertrain` brut + profil moteur | `powertrain`, `alerts` | 20 Hz |
| `TripStats` | `powertrain`, `motion`, `session` | `trip` | calcul 50 Hz, publication 20 Hz |
| `Dynamics` | vitesse, régime, roues, transmission | `wheels`, `motion`, `dynamics` | 20 Hz |
| `SessionManager` | contact, vitesse, état de session | `session` + fichiers trajet | 2 Hz |
| `Diag` | contact et réponses OBD | `diagnostics` | 2 Hz / à la demande |
| `Monitor` | processus Python et threads | `system.telemetry` | configurable, 1 Hz par défaut |
| `Noise` | microphone | `environment` | callback audio, FFT configurable |
| `USB_Storage` | `StorageManager` | `system.storage*` | 0,5 Hz |

Un service métier ne lit pas le bridge Qt. Il reçoit `VehicleRuntime` et lit des
snapshots ; seul le bridge traduit ensuite ces domaines pour QML. Les services
qui doivent déclencher une notification reçoivent un callback d’événement, ce
qui évite une dépendance inverse vers l’interface.

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

`DashboardBridge` n'expose que les propriétés structurées. Les cinq styles
livrés lisent leurs valeurs d'affichage via les propriétés sémantiques de
`UiState.qml`. Les pages développeur peuvent explorer les domaines et leur
métadonnée, sans reconstruire une carte plate.

Les anciens contrats `bridge.data`, `bridge.stats`, `bridge.systemHealth` et
`bridge.storageStatus` ont été supprimés. Les alias `coasting_km` et `g_force`
n'existent plus ; les noms physiques sont
`deceleration_without_throttle_km` et `longitudinal_g`.

La surface Qt est volontairement limitée à : `vehicleState`, `tripState`,
`diagnosticsState`, `systemState`, `sessionState`, `calibrationState`,
`presentationState`, `dataQuality` et `config`. Les signaux Qt portent le même
nom avec le suffixe `Changed`. Les dashboards n'appellent aucun slot : ils
émettent `commandRequested` et `settingsRequested`. `AppShell` centralise les
routes, l'historique, les confirmations et la journalisation de la vitesse,
puis appelle `executeUiCommand`.

## Déploiement et données

Le code versionné vit dans `/opt/clios/releases/<version>` et le lien atomique
`/opt/clios/current` désigne la release active. Les données suivent la priorité
USB CliOS, `/var/lib/clios` sur racine persistante, puis `/run/clios` lorsque la
racine est un OverlayFS. Le lanceur restaure N-1 si la nouvelle release ne pose
pas son marqueur de santé.

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
