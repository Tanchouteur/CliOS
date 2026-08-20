# Checklist release / livraison CliOS

- [ ] `VERSION`, tag et manifeste ont la même version SemVer.
- [ ] Python compile, tests, QML compile/smoke, JSON validation et `bash -n` passent.
- [ ] L’archive ARM64 Bookworm et les dépendances verrouillées sont publiées avec SHA-256.
- [ ] Staging et self-check ne modifient pas `/opt/clios/current`.
- [ ] Activation, marqueur de santé et rollback N-1 sont testés.
- [ ] Compatibilité de lecture N-1 et sauvegardes de migration vérifiées.
- [ ] Installation Debian Bookworm validée dans Docker.
- [ ] Test matériel Pi 4 et Pi 5, écran 1920×720 et interface CAN réelle effectué.

English: verify matching SemVer metadata, all CI gates, SHA-256 artifacts, isolated staging, first-boot rollback, N-1 data reads, Docker Bookworm installation, and real Pi 4/5 hardware before a stable release.

Production locale : `python3 tools/build_release.py --channel stable --base-url https://releases.example/`.
