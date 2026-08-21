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

Sur une installation kiosk sans bureau, udev demande à systemd de monter les
partitions de stockage USB sous `/media/clios/<périphérique>`. Le montage est
lié à la présence du périphérique et le dossier de données `clios/` est créé
avec les droits du groupe `clios`. FAT, exFAT, NTFS et les systèmes de fichiers
Linux pris en charge par le noyau sont acceptés.

## Compatibilité et retour arrière

Les formats de données garantissent la lecture N-1. Les migrations sont
additives ou réversibles et précédées d’une sauvegarde.

## Vérifications réalisées

Tests de détection OverlayFS depuis les montages, contrat udev/systemd,
priorités USB/interne/RAM, transitions de stockage et migration non destructive.
