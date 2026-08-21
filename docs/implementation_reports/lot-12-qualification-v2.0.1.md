# Lot 12 — Qualification et publication v2.0.1

## Qualification automatisée

La suite simule une installation stable, la découverte/staging d'une RC,
l'activation saine, l'échec du premier démarrage et le rollback. Les cas
d'archive corrompue et de téléchargement interrompu restent couverts par la
suite historique. Les huit états QML et la confirmation mobile sont contractuels.

Le 21 août 2026, la qualification locale de la branche a validé 91 tests,
la compilation Python, les scripts shell, le schéma JSON et les données. Le
self-check équivalent CI a aussi été exécuté dans Debian Bookworm ARM64 : les
18 wheels du lock s'installent sans réseau, `pip check` et les imports critiques
réussissent, puis le smoke test valide 35 vues et 13 états en 1920×720.

## Publication

`VERSION` cible `2.0.1-rc.1`. Après fusion dans `main`, le tag correspondant
déclenche la publication automatique de la RC. Le tag stable `v2.0.1` ne doit
être créé qu'après la fiche `docs/qualification_v2.0.1.md` entièrement validée.

## Matériel restant

La validation Raspberry Pi 5 ne peut pas être exécutée en CI et reste une porte
manuelle. La validation Pi 4 est explicitement différée dans les notes de
version.
