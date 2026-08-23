# Mode mock sous Windows

CliOS peut être essayé sans véhicule ni matériel CAN sous Windows 10 ou 11 64 bits.
Double-cliquez sur `clios-windows.cmd` à la racine du dépôt. Le premier lancement
peut prendre plusieurs minutes : le lanceur cherche Python 3.12 x64, l'installe
avec `winget` pour l'utilisateur courant si nécessaire, crée `.venv`, puis installe
les dépendances. Les lancements suivants réutilisent cet environnement tant que
`requirements.txt` n'a pas changé.

## Dépannage

- **Avertissement SmartScreen** : vérifiez que le dépôt provient bien de
  `Tanchouteur/CliOS`, puis choisissez **Informations complémentaires** et
  **Exécuter quand même**. Le script ne demande pas de droits administrateur.
- **`winget` absent ou bloqué** : installez manuellement Python 3.12 x64 depuis
  [python.org](https://www.python.org/downloads/windows/), en autorisant son ajout
  au `PATH`, fermez la fenêtre puis relancez le lanceur. `winget` est normalement
  fourni par *App Installer* sur les versions actuelles de Windows.
- **Environnement endommagé** : ouvrez `cmd.exe` dans le dossier CliOS et lancez
  `clios-windows.cmd -ResetEnvironment`. Le dossier `.venv` sera recréé.
- **Fenêtre trop grande ou trop petite** : utilisez par exemple
  `clios-windows.cmd -Scale 0.8`. La valeur par défaut est `0.65`.
- **Diagnostic** : chaque exécution écrit un journal horodaté dans
  `logs\windows-launcher`. En cas d'erreur, son chemin exact reste affiché dans la
  fenêtre.

## Options utiles

```bat
clios-windows.cmd -SetupOnly
clios-windows.cmd -SmokeTest
clios-windows.cmd -ResetEnvironment -Scale 0.65
```

`-SetupOnly` prépare l'environnement sans ouvrir l'interface. `-SmokeTest` charge
l'application avec Qt hors écran, la ferme automatiquement et renvoie un code
d'erreur exploitable par une CI. Les arguments non reconnus par le lanceur sont
transmis à `main.py`.
