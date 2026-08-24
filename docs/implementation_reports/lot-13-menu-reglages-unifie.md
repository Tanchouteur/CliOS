# Lot 13 — Menu de réglages unifié

## Ce qui change concrètement pour toi

Le cockpit ouvre désormais un espace de réglages unique adapté à l’écran
1920×720. Un rail latéral permanent donne accès à Conduite, Apparence,
Véhicule, Système et Avancé, ainsi qu’à un retour direct au cockpit.

Conduite regroupe les trajets et l’état essentiel du véhicule. Apparence réunit
les styles, l’accent et les éclairages BLE. Véhicule contient l’entretien, le
diagnostic OBD et la transmission. Système centralise le réseau, les mises à
jour, le stockage et l’alimentation. Les profils, services, données CAN,
journaux et exports sont regroupés dans Avancé.

Le réseau n’affiche que les profils Wi-Fi déjà mémorisés par NetworkManager. La
protection OverlayFS indique séparément son état actuel et sa configuration à
appliquer au prochain redémarrage.

## Ce que tu dois faire

Rien pour les installations existantes. NetworkManager et `nmcli` doivent être
présents pour utiliser l’onglet Réseau. Les profils Wi-Fi doivent être créés en
dehors de CliOS avant d’apparaître dans la liste.

## Développement et livraison

Le lot est développé sur `feature/unified-settings-menu` depuis `main` et porte
la version `2.0.1-rc.14`. Les opérations réseau transitent par
`executeUiCommand`; aucun slot ni signal n’est ajouté au méta-objet public Qt
v1. Les anciennes routes du Theme API v1 restent acceptées et sont traduites
vers la nouvelle rubrique correspondante.

Le smoke test couvre les cinq thèmes officiels, les cinq rubriques et leurs
onglets. Une publication bêta éventuelle doit suivre la checklist habituelle ;
ce lot ne crée ni tag ni release automatiquement.

## Compatibilité et retour arrière

Theme API v1 et le snapshot du bridge restent inchangés. `openMaintenanceMenu`,
F12 et les anciennes routes ouvrent Système → Stockage. Le composant historique
de maintenance reste dans le dépôt pour la compatibilité structurelle, mais
n’est plus instancié visuellement.

Un retour arrière Git ne nécessite aucune migration de données. Les profils
réseau et la configuration OverlayFS restent gérés par le système.

## Vérifications réalisées

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests` : 222 tests
  et 10 sous-tests réussis ;
- `QT_QPA_PLATFORM=offscreen .venv/bin/python tools/qml_smoke.py` : 80 vues et
  14 états rendus en 1920×720 ;
- 94 captures PNG vérifiées en 1920×720 ;
- snapshot de l’API publique du bridge inchangé ;
- `git diff --check` sans erreur.
