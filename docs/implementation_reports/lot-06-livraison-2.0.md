# Lot 06 — Livraison communautaire CliOS 2.0

## Ce qui change concrètement pour toi

La cible garantie est désormais explicite : Raspberry Pi OS Bookworm 64 bits,
Pi 4/5 et écran 1920×720. Les autres plateformes et résolutions restent utiles
au développement, mais sont expérimentales pour le déploiement automobile.

## Ce que tu dois faire

Utiliser le modèle d’issue CliOS et joindre le bundle diagnostic avec le Pi,
l’écran, l’interface CAN, le véhicule, le mode de stockage et la version.

## Développement et livraison

`VERSION`, le tag et le manifeste d’une livraison doivent partager la même
version. Les parcours thème, véhicule et service sont documentés en français et
en anglais. La checklist de release est obligatoire avant un tag stable.

## Compatibilité et retour arrière

Theme API v1 et schémas v1 sont garantis pour la série 2.x. Une rupture exige
une nouvelle version majeure de l’API.

## Vérifications réalisées

Documentation, modèles GitHub, métadonnées 2.0.0 et checklist de livraison ont
été alignés avec les contrats implémentés.
