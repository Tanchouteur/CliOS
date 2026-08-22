# Lot 12 — Qualification et publication v2.0.1

## Qualification automatisée

La suite simule l'installation, la découverte et le staging d'une RC,
l'activation saine, l'échec du premier démarrage et le rollback N-1. Les cas
d'archive corrompue, de manifeste ou signature altérés et de téléchargement
interrompu sont également couverts.

Le 22 août 2026, la qualification locale de la branche RC10 a validé :

- 183 tests Python en mode Qt hors écran ;
- Ruff et le périmètre mypy progressif ;
- tous les profils, thèmes, configurations CAN et manifestes officiels ;
- la syntaxe des scripts d'installation et de maintenance ;
- 40 vues QML et 14 états en 1920x720.

La CI GitHub répète ces portes sous Python 3.11 et 3.13, exécute l'audit des
dépendances, CodeQL et les installations Docker Bookworm/Trixie. Le workflow de
release construit ensuite les deux archives ARM64, installe leurs wheelhouses
hors ligne, lance `pip check` et le smoke QML avant toute publication.

## Évolution des candidates

Les premières RC ont révélé successivement des défauts réels de staging du
`.venv`, de permissions du helper, de validation des tags, de marqueur de santé,
de démarrage headless, de navigation, d'extinction pendant une mise à jour et de
sélection du stockage USB. Ces défauts ont été corrigés avant RC10 avec des
tests de non-régression associés.

`VERSION` cible `2.0.1-rc.10`. Après fusion dans `main`, le tag
`v2.0.1-rc.10` déclenche une publication bêta. La stable sera une nouvelle
release construite avec `VERSION=2.0.1` et le tag `v2.0.1`, jamais un simple
changement du statut GitHub de la préversion.

## Porte matérielle restante

La CI ne peut pas reproduire le Raspberry Pi, Cage, la carte SD, le support USB,
le véritable adaptateur CAN ni le véhicule. La fiche
`docs/qualification_v2.0.1.md` constitue donc la dernière porte manuelle. Elle
doit être complétée avec RC10 avant le tag stable. La qualification Raspberry
Pi 4 reste différée et ne bloque pas 2.0.1.
