# Lot 09 — Assets ARM64 et publication automatique

## Ce qui change concrètement pour toi

Un tag `v*` valide construit en parallèle les archives Bookworm et Trixie ARM64,
leurs manifestes de canal et `SHA256SUMS`. La release GitHub n'est créée qu'après
CI, Docker installateur, construction des deux wheelhouses et self-checks ARM64.

## Développement et livraison

Le workflow refuse un tag différent de `VERSION` ou un commit absent de
`main`. Les préversions deviennent des GitHub prereleases. Le lock CPython 3.11
contient les hashes PyPI et chaque wheelhouse est construit sous QEMU ARM64. Un
cache indexé par lock évite de recompiler `pyo` à chaque tag.

## Compatibilité

PySide6 est fixé à 6.8.0.2 : ses wheels ARM64 manylinux_2_31 sont compatibles
avec la glibc de Bookworm, contrairement aux wheels ARM64 6.8.3.
