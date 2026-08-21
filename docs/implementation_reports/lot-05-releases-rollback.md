# Lot 05 — Releases, mise à jour et rollback

## Ce qui change concrètement pour toi

La production ne fait plus de `git pull`. Une nouvelle version est téléchargée
et vérifiée sans toucher à celle qui roule. L’activation ne se fait qu’après le
self-check et le premier démarrage revient automatiquement à N-1 s’il ne publie
pas son marqueur de santé.

## Ce que tu dois faire

Utiliser `tools/release_cli.py` en production. `update.sh` reste réservé au
développement.

## Développement et livraison

Le cycle est `check`, `stage`, `activate`, puis éventuellement `rollback`.
L’archive et chaque fichier manifesté sont contrôlés par SHA-256. Le lien
`/opt/clios/current` est changé atomiquement.

## Compatibilité et retour arrière

La version active, la précédente et la dernière stable sont protégées du
nettoyage. Une archive corrompue, un téléchargement interrompu ou un self-check
en erreur ne change jamais la version active.

## Vérifications réalisées

Tests d’archive corrompue, téléchargement interrompu, activation atomique,
marqueur de santé et rollback N-1.
