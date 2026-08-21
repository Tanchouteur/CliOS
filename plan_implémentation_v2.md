  # Plan d’implémentation CliOS 2.0

  ## Résumé

  Faire converger CliOS vers une plateforme communautaire stable en six lots successifs et toujours testables. La cible officielle est Raspberry Pi OS Bookworm 64 bits sur Pi 4/5, écran
  1920×720. Les thèmes officiels partagent une interface de réglages unique, les extensions locales restent du code de confiance, et les mises à jour utilisent des releases versionnées
  avec rollback.

  ## 1. Contrats, corrections et CI

  - Corriger l’appel inexistant `switchProfile()` et ajouter un test qui compare chaque référence `bridge.*` QML avec la surface réellement exposée.
  - Ajouter GitHub Actions avec comme contrôles bloquants :
    - compilation Python ;
    - 59 tests existants et nouveaux tests ;
    - compilation et smoke test QML offscreen ;
    - navigation dans toutes les routes de chacun des cinq thèmes ;
    - validation des JSON et manifestes ;
    - `bash -n` et test Docker de l’installateur.
  - Étendre le smoke test pour cliquer les commandes principales, charger les états manquants/erreur et vérifier qu’aucune erreur QML n’est émise.
  - Rendre `SystemOrchestrator.stop_all()` tolérant aux erreurs individuelles et signaler les workers qui ne s’arrêtent pas.
  - Supprimer `os._exit()` du parcours normal : toutes les sorties passent par Qt, puis par le `finally` principal, avec fermeture unique du bridge, du stockage, des services et des logs.
  - Ajouter `.DS_Store` au `.gitignore`. Préserver la modification utilisateur déjà présente dans `SECURITY.md`.

  ## 2. AppShell, réglages communs et Theme API v1

  - Faire posséder à `frontend/main.qml` un `AppShell` global contenant :
    - `DashboardHost` pour le thème ;
    - `SettingsShell` plein écran ;
    - dialogue de confirmation commun ;
    - notifications, maintenance et bannière de conduite.
  - Définir les routes uniques `home`, `appearance`, `vehicle`, `services`, `system`, `diagnostic` et `developer`. Le shell gère retour, navigation, historique et restauration du cockpit.
  - Transformer les pages partagées en seule implémentation fonctionnelle. Elles utilisent la palette active, les métriques communes et une barre système constante.
  - Imposer aux dashboards Theme API v1 :
    - lecture des données uniquement via `UiState` ;
    - signaux `settingsRequested(route)` et `commandRequested(command)` ;
    - aucune navigation par chemin vers `shared_pages` ;
    - aucun appel direct à `bridge` dans `frontend/styles`.
  - Centraliser les commandes et confirmations : reset des trips, entretien, session, changement de profil, quitter, redémarrer, éteindre et maintenance.
  - Au-dessus de 5 km/h, afficher un avertissement global persistant mais laisser les interactions et actions système possibles avec leur confirmation normale, conformément au choix
  produit. Journaliser ces actions avec la vitesse courante.
  - Migrer immédiatement GT, Apex, Atelier Luxe, JDM Mugen et Legacy :
    - Legacy devient pleinement compatible ;
    - le tiroir Luxe est remplacé par un lanceur thémé vers le shell ;
    - les copies de pages devenues inutilisées sont supprimées ;
    - toutes les fonctions communes sont accessibles depuis tous les thèmes.
  - Étendre `style.json` avec `apiVersion: 1`, `minCliOSVersion`, `supportedResolutions: ["1920x720"]` et `capabilities`.
  - Refuser un manifeste incompatible, expliquer l’erreur dans les diagnostics et charger GT Modern comme secours.
  - Autoriser un répertoire de thèmes de développement uniquement en mode développeur. Un thème local ne peut pas remplacer un identifiant officiel et affiche un avertissement indiquant
  que le QML est du code de confiance non sandboxé.

  ## 3. Contrats communautaires et SDK

  - Publier des JSON Schemas versionnés pour :
    - manifeste de thème ;
    - configuration véhicule ;
    - dictionnaire CAN ;
    - catalogue de profils.
  - Valider les données au démarrage et via des commandes développeur pour un thème ou un couple configuration/CAN.
  - Ajouter `schema_version: 1` aux données officielles et migrer les anciennes configurations avec sauvegarde préalable.
  - En cas de profil véhicule invalide, entrer en mode récupération : ne pas démarrer le service CAN avec un profil arbitraire, afficher l’erreur et ouvrir la gestion des profils.
  - Corriger le générateur de profil afin qu’il produise une configuration conforme au schéma réel, et enrichir le générateur de thème avec le manifeste v1, les signaux requis et un test
  minimal.
  - Formaliser Service API v1 autour de `BaseService` : identifiant stable, métadonnées, paramètres typés, santé et cycle de vie.
  - Fournir un template de service et ses tests, mais conserver un registre statique : tout service Python doit être intégré au dépôt après revue, sans chargement dynamique de code
  externe.
  - Documenter en français et en anglais trois parcours autonomes : créer un thème, adapter un véhicule, développer un service.

  ## 4. Stockage et compatibilité des données

  - Séparer code et données :
    - releases dans `/opt/clios/releases/<version>` ;
    - lien atomique `/opt/clios/current` ;
    - données internes dans `/var/lib/clios` ;
    - données volatiles explicites dans `/run/clios`.
  - Appliquer la priorité suivante :
    1. clé USB CliOS disponible ;
    2. `/var/lib/clios` si la racine est réellement persistante ;
    3. `/run/clios` si OverlayFS protège la SD ou si le stockage interne est indisponible.
  - Détecter OverlayFS depuis les montages plutôt qu’avec un simple test d’écriture, puisque la couche supérieure RAM paraît inscriptible.
  - Conserver l’état `MODE RAM` dans l’UI et migrer vers l’USB sans écrasement lors d’un branchement.
  - Lors d’une mise à niveau d’une installation existante, copier les données dynamiques vers le nouveau stockage sans supprimer l’original et produire un rapport de migration.
  - Garantir une compatibilité des données N-1 : migrations additives ou réversibles, sauvegarde avant activation et tests de lecture par la version précédente.

  ## 5. Releases, mise à jour et rollback

  - Remplacer la mise à jour UI par `git pull` par un gestionnaire de releases. `update.sh` reste éventuellement un outil de développement, jamais invoqué en production.
  - Produire pour chaque release stable ou bêta :
    - archive applicative CliOS 2.0 ;
    - dépendances verrouillées pour Raspberry Pi OS Bookworm/Python 3.11 ARM64 ;
    - manifeste SHA-256.
  - Exposer les opérations `check`, `download/stage`, `activate` et `rollback`.
  - Télécharger et préparer une release sans toucher à la version active, vérifier tous les SHA-256, installer son environnement isolé puis exécuter un self-check Python/QML/configuration.
  - Après validation, demander une confirmation dans le shell. L’activation change atomiquement le lien `current` et redémarre CliOS.
  - Le lanceur supervise le premier démarrage. Sans marqueur de santé dans le délai défini, il restaure le lien précédent et redémarre automatiquement l’ancienne version.
  - Conserver au minimum la version active et la précédente ; nettoyer seulement les releases plus anciennes non actives.
  - Stable est le canal par défaut. Bêta est un choix développeur persistant et permet toujours un retour vers la dernière stable.
  - Adapter le service systemd pour lancer `/opt/clios/current` et ne plus dépendre du chemin du clone Git.

  ## 6. Livraison CliOS 2.0 et communauté

  - Aligner `VERSION`, tag et release sur `2.0.0`.
  - Mettre à jour README, architecture, contribution, sécurité, modèles d’issues et checklist de release dans les deux langues.
  - Remplacer le modèle de bug générique par les informations utiles : Pi, écran, interface CAN, véhicule, mode stockage, version et bundle diagnostic.
  - Clarifier que 1920×720 est la résolution garantie et que les autres formats sont expérimentaux.
  - Publier la politique de compatibilité : Theme API v1 et schémas v1 restent stables pendant la série 2.x ; toute rupture future nécessite une nouvelle version majeure d’API.
  - Livrer les lots sous forme de commits séparés, chaque lot devant laisser compilation, tests, smoke QML et validations au vert.

  ## Tests d’acceptation

  - Les cinq thèmes ouvrent chaque page commune, reviennent au cockpit et utilisent les mêmes comportements.
  - Aucun fichier de thème officiel ne référence directement `bridge`.
  - Tous les boutons et commandes QML correspondent à une API existante.
  - Une page, un thème ou un profil invalide produit un diagnostic lisible et un fallback sûr.
  - Une exception pendant l’arrêt d’un service n’empêche pas les autres de s’arrêter.
  - Quitter ou redémarrer vide toutes les écritures sans arrêt brutal.
  - OverlayFS actif sélectionne explicitement `/run/clios`, même si `/var/lib/clios` semble inscriptible.
  - Les transitions RAM/USB/interne conservent les données et gèrent les conflits.
  - Une archive corrompue, un téléchargement interrompu ou un self-check en échec ne modifie jamais la version active.
  - Un premier démarrage défaillant restaure automatiquement N-1.
  - Les données créées par N restent lisibles par N-1.
  - L’installateur et la mise à niveau passent sur Debian Bookworm propre en conteneur, puis font l’objet d’un test réel Pi 4/5 avant la release stable.

  ## Hypothèses retenues

  - Les fonctionnalités évoquées dans la revue sont incluses ; GPS, médias, CarPlay et autres nouvelles fonctions produit restent hors de cette convergence.
  - Les thèmes locaux sont explicitement considérés comme du code de confiance, sans promesse de sandbox.
  - Les releases utilisent SHA-256 sans signature cryptographique indépendante.
  - macOS, Windows et Linux x86 restent supportés pour le développement et le mode mock, sans garantie de déploiement automobile.
  - La rupture des anciens thèmes est immédiate avec CliOS 2.0.0 ; aucun adaptateur Theme API historique n’est conservé.