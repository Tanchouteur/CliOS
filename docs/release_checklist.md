# Checklist release / livraison CliOS

- [ ] `VERSION`, tag et manifeste ont la même version SemVer.
- [ ] Python compile, tests, QML compile/smoke, JSON validation et `bash -n` passent.
- [ ] Les archives ARM64 Bookworm et Trixie et leurs dépendances verrouillées sont publiées avec SHA-256.
- [ ] Staging et self-check ne modifient pas `/opt/clios/current`.
- [ ] Activation, marqueur de santé et rollback N-1 sont testés.
- [ ] Compatibilité de lecture N-1 et sauvegardes de migration vérifiées.
- [ ] Installations Debian Bookworm et Trixie validées dans Docker ARM64.
- [ ] Test matériel Pi 5, écran 1920×720 et interface CAN réelle effectué (Pi 4 différé pour v2.0.1).
- [ ] Le compte rendu du lot est ajouté dans `docs/implementation_reports/`.
- [ ] Le canal du manifeste est correct : `stable` pour une livraison validée, `beta` pour une préversion.

English: verify matching SemVer metadata, all CI gates, SHA-256 artifacts, isolated staging, first-boot rollback, N-1 data reads, Docker Bookworm/Trixie installations, and real Pi 4/5 hardware before a stable release.

Production locale RC : `python3 tools/build_release.py --channel beta --target trixie-arm64 --base-url https://github.com/Tanchouteur/CliOS/releases/download/v2.0.1-rc.3`.

Gestion du canal installé :

```bash
python3 tools/release_cli.py channel          # affiche le canal courant
python3 tools/release_cli.py channel beta     # reçoit les préversions
python3 tools/release_cli.py channel stable   # revient aux versions validées
python3 tools/release_cli.py check            # interroge uniquement GitHub Releases
python3 tools/release_cli.py stage 2.0.1-rc.3 # demande le staging au helper root
python3 tools/release_cli.py rollback --stable
```
