# CliOS v2.0.1

## RC4

- machine d’état d’alimentation déterministe fondée sur le contact et le silence CAN monotone ;
- extinction ordonnée, simulée hors Linux/mode voiture, commande sans shell et règle Polkit limitée ;
- transport ISO-TP multi-ECU strict avec Flow Control physique ;
- schémas JSON autoritaires au démarrage et en CI, avec mode récupération ;
- bootstrap Ed25519 des releases, chaîne CI durcie et provenance attestée ;
- identité CliOS, documentation matérielle/sécurité/confidentialité et provenance des assets harmonisées.

La stable 2.0.1 reste conditionnée à la qualification réelle en voiture décrite dans `docs/qualification_v2.0.1.md`.

Cette version consolide la livraison ARM64 Bookworm/Trixie et remplace les mises à
jour fondées sur Git par une chaîne GitHub Releases vérifiée par SHA-256.

## Mise à jour

- catalogue officiel GitHub avec canaux stable et bêta, SemVer complet, ETag et cache ;
- archives installables Bookworm/Python 3.11 et Trixie/Python 3.13, manifestes v1 et `SHA256SUMS` produits à chaque tag ;
- wheelhouses ARM64 par plateforme et locks Python strictement versionnés et hashés ;
- staging isolé, activation atomique, contrôle du premier démarrage et rollback N-1 ;
- cockpit avec états détaillés, recherche réseau limitée à une fois par 24 h et diagnostic updater.
- montage automatique des clés de données USB par udev/systemd, y compris sans bureau graphique.
- installation initiale transactionnelle sans recopier les fichiers Qt du `.venv`.

## Sécurité

Le cockpit ne transmet jamais d'URL, de chemin ni de commande au helper root.
La seule source autorisée est définie dans `/etc/clios/updater.json` et les
self-checks s'exécutent sous l'utilisateur non privilégié `clios`.

## Matériel

La qualification finale cible Raspberry Pi 5, Raspberry Pi OS Bookworm ou Trixie 64 bits,
écran 1920×720 et interface CAN réelle. La validation Raspberry Pi 4 est
explicitement différée à une version ultérieure.
