# Lot 03 — Contrats communautaires et SDK

## Ce qui change concrètement pour toi

Un thème, un profil véhicule ou un dictionnaire CAN invalide fournit maintenant
une erreur lisible. Un profil véhicule invalide ouvre le mode récupération au
lieu de démarrer le CAN avec une configuration arbitraire.

## Ce que tu dois faire

Ajouter `schema_version: 1` aux données communautaires et les contrôler avec :

```bash
python3 tools/validate_data.py --all
```

## Développement et livraison

Les schémas v1 décrivent manifestes de thème, configurations véhicule,
dictionnaires CAN et catalogues de profils. Les générateurs de thème et de
profil produisent ces contrats. Service API v1 fournit métadonnées, paramètres
typés, santé et cycle de vie ; les services Python restent enregistrés
statiquement après revue.

## Compatibilité et retour arrière

Les anciennes données sont sauvegardées avant migration vers v1. Theme API v1
et schémas v1 restent stables pendant toute la série 2.x.

## Vérifications réalisées

Validation des données officielles, tests des générateurs, du mode récupération
et du template de service.
