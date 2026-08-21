# Lot 01 — Contrats, corrections et CI

## Ce qui change concrètement pour toi

Une erreur de nom de commande QML ne peut plus rester invisible jusqu’au
démarrage dans la voiture. L’arrêt normal passe par Qt et ferme une seule fois
le bridge, le stockage, les services et les journaux. Si un service refuse de
s’arrêter, les autres sont tout de même arrêtés et le défaut est signalé.

## Ce que tu dois faire

Avant une fusion, attendre que les jobs `python-qml` et `installer` de GitHub
Actions soient verts. Les rendre obligatoires dans le ruleset de `main` pour
bloquer réellement une fusion rouge. En local, utiliser les commandes de
`CONTRIBUTING.md`.

## Développement et livraison

Chaque `push` et Pull Request déclenche compilation, tests, validation des
données, smoke QML et contrôle de l’installateur. Une branche verte n’est pas une
release : elle peut être revue puis fusionnée dans `main`.

## Compatibilité et retour arrière

Aucune migration de données. Les sorties brutales par `os._exit()` ne font plus
partie du parcours normal.

## Vérifications réalisées

Tests de surface du bridge, navigation QML, arrêt tolérant aux erreurs,
compilation Python et validation shell.
