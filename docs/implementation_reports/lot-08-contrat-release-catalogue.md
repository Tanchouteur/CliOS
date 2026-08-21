# Lot 08 — Contrat de release et catalogue GitHub

## Ce qui change concrètement pour toi

Les versions finales suivent le canal stable et toute préversion SemVer le canal
bêta. Le catalogue public est GitHub Releases ; une version installée ou plus
ancienne n'est jamais proposée.

## Développement et sécurité

`ReleaseCatalog.check(channel, current_version)` valide les tags, l'état
draft/prerelease, le manifeste v1 et la présence de l'archive. La configuration
root `/etc/clios/updater.json` ne contient qu'un dépôt GitHub. ETag, cache,
limitation d'API, hors-ligne et JSON invalide ont des erreurs distinctes.

## Vérifications réalisées

Tests SemVer, contradiction canal/version, chemins de manifeste, sélection
stable/bêta, seuil de version et cache hors-ligne.
