# Lot 04 — Stockage et compatibilité des données

## Ce qui change concrètement pour toi

Le code installé et les données ne partagent plus le même emplacement. CliOS
préfère une clé USB compatible, sinon le stockage interne persistant, sinon la
RAM lorsque OverlayFS protège la carte SD. L’écran conserve l’indication
`MODE RAM`.

## Ce que tu dois faire

Rien pour un démarrage normal. Lors d’une ancienne installation, consulter le
rapport de migration avant de supprimer manuellement les données historiques :
la migration ne supprime jamais la source.

## Développement et livraison

Les releases vivent sous `/opt/clios/releases`, l’active sous
`/opt/clios/current`, les données sous `/var/lib/clios` et le volatile sous
`/run/clios`. Le branchement USB déclenche une copie sans écrasement avec
gestion explicite des conflits.

## Compatibilité et retour arrière

Les formats de données garantissent la lecture N-1. Les migrations sont
additives ou réversibles et précédées d’une sauvegarde.

## Vérifications réalisées

Tests de détection OverlayFS depuis les montages, priorités USB/interne/RAM,
transitions de stockage et migration non destructive.
