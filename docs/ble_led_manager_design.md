# Gestionnaire universel d'éclairages BLE

## Statut

Idée tracée pour une version ultérieure à CliOS 2.0.1. Ce chantier ne doit pas
retarder ni modifier RC10 pendant sa qualification.

## Objectif

Remplacer la configuration figée « Habitacle » et « Plancher » par une liste
libre d'appareils BLE. L'utilisateur doit pouvoir découvrir ses contrôleurs,
les tester, les nommer et les organiser sans saisir manuellement une adresse
dans un paramètre technique.

## Expérience utilisateur cible

Une page **Éclairages BLE** propose les actions suivantes :

1. lancer une recherche des appareils proches ;
2. afficher les candidats avec nom annoncé, identifiant BLE ou adresse MAC,
   puissance du signal et services connus ;
3. sélectionner un appareil et lancer un assistant de test visuel ;
4. confirmer le protocole qui a produit la couleur attendue ;
5. donner un nom libre à l'appareil, par exemple « Portière gauche »,
   « Console » ou « Coffre » ;
6. ajouter l'appareil à la liste persistée ;
7. choisir une couleur, une luminosité et un état propres à chaque appareil ;
8. placer plusieurs appareils dans un groupe et les piloter ensemble ;
9. activer un groupe global « Tous les éclairages » pour synchroniser tout le
   véhicule en une seule action.

La suppression d'un appareil ne doit effacer ni les autres appareils ni leurs
groupes. Un contrôleur temporairement absent reste configuré et apparaît comme
déconnecté.

## Modèle de données envisagé

Chaque appareil possède au minimum :

- un identifiant CliOS stable, indépendant de son nom affiché ;
- son nom choisi par l'utilisateur ;
- son identifiant BLE de plateforme et, lorsque disponible, son adresse MAC ;
- le nom et les données d'annonce observés lors du dernier scan ;
- le protocole, la caractéristique GATT et le mode d'écriture confirmés ;
- son état actif, sa couleur, sa luminosité et ses groupes ;
- la date de dernière connexion et un état de santé lisible.

L'identifiant BLE doit rester une chaîne opaque : Linux fournit généralement
une adresse MAC, tandis que macOS peut fournir un UUID. Les secrets ou données
d'appairage du système ne doivent pas être exportés dans la configuration.

Les anciennes clés `dash_*` et `foot_*` devront être migrées une seule fois vers
deux appareils nommés « Habitacle » et « Plancher », puis rester lisibles pour
permettre un rollback vers une version antérieure.

## Assistant de détection de protocole

L'assistant réutilisera la logique du script `tools/scan_ble_leds.py` :

- choix explicite de la caractéristique GATT lorsqu'il en existe plusieurs ;
- respect de `write` ou `write-without-response` selon ses propriétés ;
- une couleur témoin différente pour chaque protocole ;
- confirmation humaine avant le test suivant ;
- possibilité de réessayer ou de changer de caractéristique ;
- journal final contenant appareil, protocole, UUID GATT et mode d'écriture ;
- possibilité d'ajouter ultérieurement un protocole sans modifier l'interface.

Un appareil n'est ajouté comme éclairage confirmé qu'après un changement visuel
validé par l'utilisateur. Les périphériques seulement « probables » restent
dans les résultats de recherche et ne sont pas enregistrés automatiquement.

Les essais matériels du 22 août 2026 ont confirmé `LOTUS_9B` sur un
`ELK-BLEDOM` via `FFF3`, puis `LEDCAR_DMX_9B` sur un `LEDCAR-01-DF02` via
`FFE1`. Les quatre dialectes historiques de CliOS ne pilotaient pas ce second
contrôleur ; ses trames RGBIC/DMX validées font désormais partie du service de
base.

Sources d'interopérabilité utilisées pour ces trames :

- [MrMcFlyy/LEDCAR-01](https://github.com/MrMcFlyy/LEDCAR-01), relevés de
  paquets de l'application LED LAMP ;
- [LycheeAPPF/led-ble-car](https://github.com/LycheeAPPF/led-ble-car),
  spécification indépendante et test matériel des dialectes A et B sur
  LEDCAR-01.

## Organisation technique proposée

- un registre de protocoles indépendant de l'interface et partagé entre le
  script de diagnostic et le service runtime ;
- un catalogue persistant d'appareils et de groupes dans le stockage CliOS ;
- un contrôleur QML dédié au scan, aux tests et aux modifications atomiques ;
- un worker BLE conservant une file limitée à la dernière couleur demandée ;
- connexions, délais et erreurs isolés par appareil afin qu'un contrôleur absent
  ne bloque pas les autres ;
- aucune recherche BLE permanente : scan uniquement à la demande avec une durée
  bornée et un bouton d'arrêt.

## Critères d'acceptation futurs

- aucun emplacement automobile n'est codé en dur ;
- ajout, renommage et suppression d'un nombre variable d'appareils ;
- contrôle individuel, par groupe et global ;
- reconnexion après redémarrage et après perte temporaire du Bluetooth ;
- migration des deux anciens contrôleurs sans perte de réglage ;
- fonctionnement avec plusieurs appareils utilisant des protocoles différents ;
- interface tactile utilisable en 1920x720 et états vide, scan, erreur et
  déconnecté couverts par le smoke QML ;
- tests unitaires du registre de protocoles, des migrations et du routage des
  couleurs sans matériel BLE.
