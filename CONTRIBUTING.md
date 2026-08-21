# Guide de contribution

Les profils véhicule, dictionnaires CAN, thèmes, images et sons doivent indiquer leur provenance, leur auteur ou propriétaire, et une licence compatible avec GPL-3.0-only. Une ressource « trouvée en ligne » sans autorisation vérifiable sera refusée. Consultez [ASSETS.md](ASSETS.md) et les parcours détaillés [français](docs/community_fr.md) / [anglais](docs/community_en.md).

Ce document définit les standards et les processus pour contribuer au projet. Le respect de ces directives permet de maintenir un historique propre, de faciliter les revues de code et d'assurer la stabilité du système.

## 1. Signaler un problème (Bug Report)

Avant de soumettre un nouveau ticket (Issue), il est requis de vérifier la base de données existante pour éviter les doublons.
Un signalement de bug valide doit obligatoirement inclure :
- Le système d'exploitation et la description du matériel utilisé (ex: modèle de Raspberry Pi, version du noyau).
- La séquence exacte d'étapes permettant de reproduire le problème.
- Le comportement attendu face au comportement observé.
- Les extraits de journaux d'erreurs (logs) formatés correctement.

## 2. Proposer une amélioration

Le développement de nouvelles fonctionnalités nécessite une validation préalable. Avant de produire du code, ouvrez un sujet dans l'onglet "Discussions" (catégorie "Ideas") pour détailler l'architecture et l'intérêt de l'ajout. Cela évite le rejet d'une Pull Request ne s'alignant pas avec la feuille de route globale.

## 3. Configuration de l'environnement

Pour initialiser le poste de développement :

1. Cloner le dépôt en local.
2. Initialiser un environnement virtuel Python (`python -m venv venv`).
3. Installer les dépendances via le fichier fourni : `pip install -r requirements.txt`.
4. Vérifier la compatibilité des dépendances graphiques (PySide6) avec le système hôte.

## 4. Processus de Pull Request (PR)

Toute intégration de code doit respecter le flux de travail suivant :

1. Créer une branche de travail dédiée à partir de la branche principale (`main`).
   - Nomenclature : `feature/nom-de-la-fonctionnalite` ou `fix/correction-du-bug`.
2. Appliquer les modifications en respectant les standards de code.
3. Vérifier que la modification n'introduit pas de régressions sur les modules existants.
4. Ouvrir une Pull Request et remplir l'intégralité du modèle de description fourni.

## 5. Standards de code

L'uniformité de la base de code est une priorité absolue.

- **Python** : Le code doit être conforme à la norme PEP 8. L'utilisation des annotations de type (Type Hints) est obligatoire pour les signatures de fonctions et de classes.
- **QML** : les dashboards officiels lisent uniquement `UiState` et émettent `settingsRequested(route)` ou `commandRequested(command)`. Aucun fichier sous `frontend/styles/<theme>` ne référence directement `bridge` ni `shared_pages`.
- **Runtime** : Toute publication backend passe par `VehicleRuntime.publish()` ou `publish_many()` avec un domaine explicite. Un nouveau signal CAN doit être ajouté à `src/signal_catalog.py`, avec unité et TTL adaptés.
- **Sessions** : Les statistiques rapides restent à 50 Hz, leurs publications à 20 Hz. Une clôture de session doit capturer les valeurs finales avant de remettre l’accumulateur à zéro.
- **Commentaires** : Les commentaires doivent justifier les choix architecturaux complexes. Ils doivent adopter un ton technique, impersonnel et concis.
- **Historique** : Les messages de commit doivent être explicites, rédigés à l'impératif, et se limiter à la modification technique apportée.

## Vérifications avant revue

```bash
python3 -m compileall -q src main.py
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen python3 tools/qml_smoke.py
python3 tools/validate_data.py --all
bash -n install.sh update.sh tools/*.sh
```

Les tests de contrat contrôlent notamment la surface publique du bridge, le
catalogue CAN et l’absence des anciennes propriétés plates dans les styles.

## Compte rendu de lot

Chaque lot fonctionnel terminé ajoute un fichier dans
`docs/implementation_reports/`, construit depuis `TEMPLATE.md`. Ce document
traduit les changements techniques en effets concrets pour l’utilisateur et le
mainteneur : nouveau parcours, commandes, impact sur les branches et releases,
compatibilité, points d’attention et vérifications réalisées.

Le processus CI, les branches, les releases et les canaux sont détaillés dans
[`docs/ci_branches_releases_fr.md`](docs/ci_branches_releases_fr.md).

## English summary

Every pull request must keep Python compilation, unit tests, the offscreen QML route smoke test, JSON/schema validation, and shell syntax checks green. Theme API v1 and schemas v1 are stable for CliOS 2.x. External Python code is never dynamically loaded: new services must be added to the static registry after review. See [the English community guide](docs/community_en.md).
