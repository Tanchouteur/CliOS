# Lot 10 — Helper de mise à jour privilégié

## Ce qui change concrètement pour toi

`clios-updater.socket` expose exclusivement `status`, `stage(version)`,
`activate(version)` et `rollback(stable_only)` au groupe `clios`. Toute URL,
chemin, commande ou clé supplémentaire venant du client est rejeté.

## Sécurité et exploitation

Le service root est isolé par systemd. Il résout GitHub lui-même, télécharge en
`.part`, contrôle l'archive et les fichiers, extrait avec le filtre sûr de
Python, installe l'environnement puis lance les checks sous `clios`. Le lien
`current` ne change qu'à l'activation et un échec de santé restaure N-1.

## Vérifications réalisées

Tests du protocole fermé, staging RC, activation saine et rollback automatique
en l'absence du marqueur de premier démarrage.
