# CliOS v2.0.1

CliOS 2.0.1 est une version de fiabilisation majeure de la série 2.0. Elle
conserve Theme API v1 et les schémas communautaires v1 tout en renforçant le
fonctionnement sur Raspberry Pi 5, la mise à jour atomique et l'utilisation en
voiture.

La dernière candidate est `v2.0.1-rc.10`. La stable reste conditionnée à la
qualification matérielle décrite dans `docs/qualification_v2.0.1.md`.

## Alimentation et fonctionnement automobile

- machine d'état déterministe fondée sur le contact et une horloge monotone ;
- protection configurable contre le silence CAN, active dès le démarrage ;
- arrêt ordonné avec sauvegarde des services et commande système contrôlée ;
- extinction réelle limitée au Raspberry Pi en mode voiture ;
- inhibition de l'extinction pendant le téléchargement, le staging et
  l'activation d'une mise à jour ;
- règle Polkit et autorisations système limitées aux opérations nécessaires.

## Mise à jour et récupération

- catalogue GitHub officiel avec canaux stable et bêta et ordre SemVer complet ;
- archives ARM64 distinctes pour Bookworm/Python 3.11 et Trixie/Python 3.13 ;
- manifestes v1, hashes SHA-256, signature Ed25519 et attestations de provenance ;
- helper privilégié à surface réduite, staging isolé et activation atomique ;
- marqueur de santé au premier démarrage et rollback N-1 automatique ou manuel ;
- progression détaillée dans le cockpit et erreurs d'autorisation corrigées ;
- précompilation Python des releases afin d'alléger leur premier démarrage.

## CAN, diagnostic et données

- transport ISO-TP strict, indépendant par ECU, avec Flow Control physique ;
- validation des longueurs, séquences, délais et réponses multi-ECU ;
- schémas JSON autoritaires au démarrage et en CI avec mode récupération ;
- activité CAN thread-safe injectée dans le service d'alimentation ;
- stockage USB monté automatiquement en environnement headless ;
- sélection prioritaire d'une clé CliOS valide, y compris lorsqu'elle contient
  déjà des données ou d'anciens exports ;
- capacité affichée issue du support réellement sélectionné et repli explicite
  vers le stockage interne ou le mode RAM.

## Cockpit et installation

- menus de maintenance unifiés pour les cinq thèmes ;
- navigation et retour depuis les pages Diagnostic et Système fiabilisés ;
- Apex choisi lors d'une première installation ;
- curseur masqué dans Cage ;
- thème japonais amélioré : placement des jauges, bouton central, traînées sans
  latence et anticrénelage des aiguilles ;
- installation transactionnelle dans `/opt/clios/releases` et consignes finales
  adaptées au service systemd ;
- démarrage à froid allégé sans attendre les cibles audio ou CAN facultatives.

## Sécurité et communauté

- dépendances auditées, CodeQL, CI Python 3.11/3.13 et actions épinglées ;
- validation des profils, thèmes, dictionnaires CAN et manifestes officiels ;
- identité CliOS, documentation matérielle, confidentialité et provenance des
  assets harmonisées ;
- guides de contribution, gouvernance, mainteneurs, support, formulaires
  d'issues et contrats QML publics.

## Matériel supporté

- Raspberry Pi 5, Raspberry Pi OS Bookworm ou Trixie 64 bits, écran 1920x720 : supporté après qualification finale ;
- Raspberry Pi 4 : expérimental ;
- macOS, Windows et x86 : développement et mode mock uniquement.

CliOS est un écran accessoire non homologué. Il ne remplace pas les instruments
obligatoires du véhicule et aucune restriction fonctionnelle fondée sur la
vitesse n'est ajoutée par cette release.
