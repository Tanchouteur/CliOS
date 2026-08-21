# CliOS 2.x community workflows

## Create a theme

Run `python3 tools/create_ui_style.py my_theme "My theme"`. It is created under `frontend/dev_styles` and is only visible with `developer.enabled: true`. Read telemetry through `UiState`, keep the `settingsRequested` and `commandRequested` signals, then validate the manifest with `tools/validate_data.py --theme ...`. Local QML is trusted, unsandboxed code and cannot replace an official theme id.

## Adapt a vehicle

Copy a v1 vehicle configuration into `data/config`, create a v1 CAN dictionary in `data/can`, and associate both in `profiles.json`. The contracts live under `schemas/v1`. Run `python3 tools/validate_data.py --vehicle ... --can ... --profiles ...`, then test with `./clios --mock`. An invalid profile opens recovery mode and leaves CAN disabled.

## Develop a service

Copy `templates/service/example_service.py`, choose a stable `service_id`, declare typed settings with `ServiceParamType`, and implement lifecycle methods. Register it in `setup_services()` and add tests. CliOS never dynamically loads external Python services; static registry integration requires repository review.
