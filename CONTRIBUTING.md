# Guide de contribution

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
- **QML** : La séparation des préoccupations est stricte. Aucune logique métier complexe ne doit résider dans les fichiers `.qml`. Le moteur UI ne doit faire que du rendu et de la transmission de signaux au pont (Bridge) Python.
- **Commentaires** : Les commentaires doivent justifier les choix architecturaux complexes. Ils doivent adopter un ton technique, impersonnel et concis.
- **Historique** : Les messages de commit doivent être explicites, rédigés à l'impératif, et se limiter à la modification technique apportée.
