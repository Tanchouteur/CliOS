# Qualification matérielle de CliOS 2.0.1

Cette fiche constitue la preuve manuelle à compléter avec
`v2.0.1-rc.10` avant de créer le tag stable. Pour chaque anomalie, conserver la
date, l'image Raspberry Pi OS, le matériel concerné et les journaux associés.

## Environnement essayé

- Date :
- Version et commit CliOS :
- Raspberry Pi : Pi 5 / autre :
- Raspberry Pi OS : Bookworm / Trixie, version :
- Écran et résolution :
- Interface CAN et firmware :
- Véhicule ou banc CAN :
- Support système : carte SD / autre :
- Support de données : clé USB / stockage interne / OverlayFS :

## Installation et démarrage

- [ ] installation propre avec `install.sh` sur Raspberry Pi OS Bookworm 64 bits ;
- [ ] installation propre avec `install.sh` sur Raspberry Pi OS Trixie 64 bits ;
- [ ] les instructions finales proposent correctement le démarrage du service ;
- [ ] `clios.service` démarre et redémarre sans intervention manuelle ;
- [ ] Apex est le thème affiché lors d'une première installation ;
- [ ] aucun pointeur de souris ne reste visible dans Cage ;
- [ ] le tactile et le rendu 1920x720 fonctionnent ;
- [ ] trois démarrages à froid consécutifs aboutissent au cockpit ;
- [ ] la durée de l'écran noir est acceptable et notée ci-dessous ;
- [ ] « Relancer CliOS » revient au cockpit sans erreur ni perte de réglage.

Temps mesurés du démarrage électrique à la première image CliOS :

1. ___ s
2. ___ s
3. ___ s

En cas de lenteur, joindre :

```bash
systemd-analyze critical-chain clios.service
systemd-analyze blame
journalctl -u clios.service -b -o short-monotonic --no-pager
```

## Mise à jour et rollback

- [ ] une installation stable 2.0.0 passée sur le canal bêta détecte RC10 ;
- [ ] une RC antérieure sur le canal bêta détecte `2.0.1-rc.10` ;
- [ ] la progression quitte « Résolution GitHub » et reste cohérente pendant le téléchargement ;
- [ ] le téléchargement, le contrôle de signature et le staging se terminent sans `EPERM` ;
- [ ] l'activation bascule bien sur RC10 ;
- [ ] le marqueur de santé valide le premier démarrage ;
- [ ] les profils, thèmes, trajets et réglages persistés sont conservés ;
- [ ] une archive interrompue ou invalide ne modifie pas `/opt/clios/current` ;
- [ ] un premier démarrage volontairement non validé déclenche le rollback N-1 ;
- [ ] le rollback manuel revient à la version précédente ;
- [ ] le rollback vers la dernière stable revient directement à 2.0.0 ;
- [ ] un bundle diagnostic contient le manifeste actif et l'erreur updater simulée ;
- [ ] après publication, RC10 détecte la stable `2.0.1` sur le canal bêta.

## Stockage et protection de la carte SD

- [ ] une clé montée sous `/media/clios/<partition>/clios` est sélectionnée en priorité ;
- [ ] une clé déjà remplie, notamment avec un ancien dossier d'export, reste acceptée ;
- [ ] l'interface affiche la capacité et l'espace libre de la clé, pas ceux de la carte SD ;
- [ ] les écritures de réglages, trajets, logs et exports arrivent sur la clé ;
- [ ] le retrait puis le retour de la clé sont détectés sans planter CliOS ;
- [ ] sans clé, le repli vers le stockage interne est explicite et fonctionnel ;
- [ ] le mode OverlayFS/RAM peut être activé et son état affiché est correct ;
- [ ] redémarrage, mise à jour et rollback restent possibles avec la configuration protégée.

## CAN, diagnostic et extinction

- [ ] réception des valeurs moteur avec une interface CAN réelle ;
- [ ] le diagnostic détecte l'adaptateur et permet de revenir au menu ;
- [ ] plusieurs calculateurs peuvent répondre sans erreur ISO-TP visible ;
- [ ] contact actif : aucun arrêt n'est déclenché, même avec un régime moteur nul ;
- [ ] contact coupé : extinction après le délai normal configuré ;
- [ ] retour du contact pendant le compte à rebours : extinction annulée ;
- [ ] aucun CAN depuis le démarrage : extinction après le délai de silence configuré ;
- [ ] adaptateur CAN débranché : le garde-fou de silence reste fonctionnel ;
- [ ] bref retour du contact puis silence CAN : arrêt après le délai prévu ;
- [ ] téléchargement, staging et activation d'une mise à jour suspendent l'extinction automatique ;
- [ ] l'arrêt sauvegarde les données et laisse des journaux exploitables.

## Cockpit et trajet

- [ ] les cinq thèmes ouvrent le même menu unifié et permettent de revenir au cockpit ;
- [ ] les pages Système, Réseau, Diagnostic, Stockage et Mise à jour sont navigables au tactile ;
- [ ] les remises à zéro Trip A et Trip B fonctionnent comme prévu ;
- [ ] le thème japonais conserve ses aiguilles nettes, ses traînées et ses jauges correctement placées ;
- [ ] aucun bandeau ou écran de récupération inattendu ne masque le cockpit ;
- [ ] un trajet normal ne provoque aucun arrêt intempestif ;
- [ ] les statistiques et données de trajet sont encore présentes après redémarrage.

## Résultat

- [ ] RC10 acceptée pour devenir CliOS 2.0.1 stable.

Observations, anomalies et liens vers les journaux :

<!-- Ajouter ici les résultats réels. -->

## Raspberry Pi 4

La qualification Pi 4 reste expérimentale et hors critère de sortie de 2.0.1.
