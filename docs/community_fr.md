# Parcours communauté CliOS 2.x

## Créer un thème

Exécutez `python3 tools/create_ui_style.py mon_theme "Mon thème"`. Le thème est créé dans `frontend/dev_styles`, donc visible uniquement avec `developer.enabled: true`. Modifiez le QML via `UiState`, conservez les signaux `settingsRequested` et `commandRequested`, puis validez le manifeste avec `tools/validate_data.py --theme ...`. Le QML local est du code de confiance non sandboxé et ne peut pas remplacer un identifiant officiel.

## Adapter un véhicule

Copiez une configuration v1 dans `data/config`, créez un dictionnaire CAN v1 dans `data/can`, puis ajoutez leur association dans `profiles.json`. Les quatre fichiers suivent les schémas de `schemas/v1`. Exécutez `python3 tools/validate_data.py --vehicle ... --can ... --profiles ...`, puis testez avec `./clios --mock`. Un profil invalide ouvre le mode récupération et le CAN reste arrêté.

## Développer un service

Copiez `templates/service/example_service.py`, choisissez un `service_id` stable, déclarez les paramètres avec `ServiceParamType` et implémentez `start/stop`. Ajoutez le service à `setup_services()` et des tests. CliOS n’effectue aucun chargement dynamique de Python externe : l’intégration au registre statique exige une revue.
