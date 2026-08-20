# Theme API v1

Un thème CliOS 2.0 est un cockpit QML de confiance. Son `Dashboard.qml` lit les données uniquement via `frontend/state/UiState.qml` et expose :

```qml
signal settingsRequested(string route)
signal commandRequested(string command)
```

Les routes communes sont `appearance`, `vehicle`, `services`, `system`, `diagnostic` et `developer`. Le thème ne charge jamais `shared_pages` lui-même et n’appelle jamais `bridge`. `AppShell` possède la navigation, les confirmations et les commandes.

Le manifeste suit `schemas/v1/theme-manifest.schema.json` avec `apiVersion: 1`, `minCliOSVersion`, `supportedResolutions: ["1920x720"]` et `capabilities`.

```bash
python3 tools/create_ui_style.py racing_red "Racing Red"
python3 tools/validate_data.py --theme frontend/dev_styles/racing_red/style.json
```

Les thèmes locaux ne peuvent pas remplacer un identifiant officiel. Ils ne sont visibles que si `developer.enabled` vaut `true` et sont du code de confiance non sandboxé.

See also: [English community guide](../../docs/community_en.md).
