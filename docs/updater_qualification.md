# Qualification de l’updater

## Boucle rapide

Les tests unitaires couvrent les phases pondérées, les erreurs structurées, le
socket Unix réel, les lectures concurrentes, A/B/C signées, l’activation saine,
le rollback automatique et la réactivation d’une release déjà préparée.

```bash
python3 -m unittest \
  tests.test_updater_service \
  tests.test_updater_socket_lab \
  tests.test_updater_signed_fixtures \
  tests.test_release_manager -v
```

Le test socket est ignoré uniquement si l’environnement local refuse la
création de sockets Unix avec `EPERM`. Il s’exécute normalement en CI Linux et
dans le laboratoire Docker.

## Laboratoire systemd Bookworm/Trixie

Le mode fixture ne nécessite aucun wheelhouse :

```bash
tools/test_updater_lab.sh --fixture
```

Le mode complet vérifie en plus les wheelhouses ARM64 déjà présents dans
`wheelhouses/bookworm-arm64` et `wheelhouses/trixie-arm64` :

```bash
tools/test_updater_lab.sh --full
```

Le workflow manuel `Updater systemd lab` expose les deux modes. Il ne crée ni
tag ni publication. Le probe transitoire reprend le durcissement de l’unité de
production et utilise uniquement `/run/clios-updater-lab`, supprimé avec
l’unité.

## Diagnostic Raspberry Pi

Le collecteur est en lecture seule et inclut journaux précis, propriétés
systemd, permissions, OverlayFS/montages, disque, Python et état des releases :

```bash
sudo /opt/clios/current/tools/collect_updater_diagnostics.py \
  --output /var/lib/clios/diagnostics/updater.json
```

Le probe ponctuel peut être lancé localement sur le Pi ou via SSH :

```bash
tools/test_updater_pi.sh
tools/test_updater_pi.sh --ssh clios@raspberrypi.local
```

Le tag `2.0.1-rc.14` reste interdit tant que Ruff, la CI, le laboratoire
complet et ce probe Pi ne sont pas tous verts.
