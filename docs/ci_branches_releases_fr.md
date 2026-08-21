# CI, branches, releases et canaux

Ce document explique le parcours normal d’une modification jusqu’à son
installation dans une voiture.

## À quoi sert la CI ?

La CI (intégration continue) est le contrôle automatique exécuté par GitHub à
chaque `push` et à chaque Pull Request. Elle répond à une question simple :
« cette modification peut-elle entrer dans le projet sans casser les contrats
déjà garantis ? »

La CI CliOS fait échouer le contrôle si l’un de ces points échoue :

- compilation Python ;
- tests unitaires et tests des contrats Python/QML ;
- validation des JSON, profils et manifestes ;
- chargement QML hors écran, avec les sept routes des cinq thèmes ;
- états d’erreur, données manquantes et confirmations du smoke test ;
- syntaxe des scripts shell ;
- installation sur Debian Bookworm dans Docker.

La CI ne remplace ni le test sur Pi 4/5 ni le test avec une vraie interface CAN.
Elle ne publie pas non plus une release toute seule : elle indique si le commit
est techniquement admissible.

Pour empêcher réellement une fusion rouge, activer dans GitHub
`Settings → Rules → Rulesets` la protection de `main`, exiger une Pull Request et
rendre obligatoires les statuts `python-qml` et `installer`. Le fichier du dépôt
définit les contrôles ; ce réglage GitHub définit leur caractère bloquant.

## Flux de branches recommandé

1. Mettre `main` à jour et créer `feature/nom-court` ou `fix/nom-court`.
2. Développer un lot cohérent et ajouter son compte rendu dans
   `docs/implementation_reports/`.
3. Exécuter les contrôles locaux indiqués dans `CONTRIBUTING.md`.
4. Pousser la branche et ouvrir une Pull Request vers `main`.
5. Attendre que les deux jobs CI soient verts, faire la revue, puis fusionner.

`main` doit toujours rester publiable. Une branche `release/2.x.y` peut être
créée temporairement lorsqu’une stabilisation nécessite plusieurs correctifs,
mais elle n’est pas obligatoire. Une fonctionnalité ne doit pas être développée
directement sur une branche de release.

## Différence entre branche, release et canal

| Notion | Sert à quoi ? | Exemple |
|---|---|---|
| Branche | Isoler du code en cours de développement | `feature/update-channel` |
| Release | Installer une version figée et vérifiable | `2.0.1` |
| Canal | Choisir le niveau de maturité des mises à jour proposées | `stable` ou `beta` |

Le canal ne change pas la branche Git de la machine. En production, CliOS
n’exécute pas `git pull` : il télécharge une archive de release, vérifie son
SHA-256, la prépare à côté de la version active, puis change atomiquement le lien
`/opt/clios/current` après validation.

## Canal stable

`stable` est le choix par défaut et celui recommandé dans une voiture utilisée
au quotidien. Il ne propose que les releases dont le manifeste porte
`"channel": "stable"` et qui ont terminé la validation prévue dans la checklist.

## Canal bêta

`beta` est un choix volontaire pour essayer des préversions. Ces versions ont
passé la CI, mais peuvent encore contenir des défauts fonctionnels ou nécessiter
des retours sur matériel réel. Le choix est mémorisé. Il peut être modifié dans
Système → Canal de mise à jour ou en ligne de commande :

```bash
python3 tools/release_cli.py channel beta
python3 tools/release_cli.py channel stable
```

Une machine en bêta peut revenir directement à la dernière stable connue :

```bash
python3 tools/release_cli.py rollback --stable
```

Le changement de canal ne télécharge et n’active rien à lui seul. Le bouton
« Mises à jour » interroge le catalogue configuré. Le staging et l’activation
restent des opérations distinctes et contrôlées.

## Créer une release

1. Choisir une version SemVer et l’écrire dans `VERSION`.
2. Vérifier que la CI est verte et compléter `docs/release_checklist.md`.
3. Construire l’archive avec le bon canal.
4. Vérifier le manifeste SHA-256 et tester le staging/self-check.
5. Créer le tag correspondant seulement après validation.
6. Publier l’archive et le manifeste dans le catalogue du même canal.

Exemple stable :

```bash
python3 tools/build_release.py --channel stable --base-url https://releases.example/
```

Une bêta utilise `--channel beta`. Une bêta validée n’est pas transformée sur
place : une nouvelle release stable est reconstruite avec sa version et son
manifeste définitifs.
