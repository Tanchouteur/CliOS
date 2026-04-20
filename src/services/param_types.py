from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, Mapping


class ServiceParamType(str, Enum):
    """Types de parametres supportes par le moteur de services."""

    SLIDER = "slider"
    TOGGLE = "toggle"
    LIST = "list"
    BUTTON = "button"
    NUMBER = "number"
    TEXT = "text"


Validator = Callable[[Any, Any, Mapping[str, Any]], Any]


def _validate_slider(value: Any, default: Any, schema: Mapping[str, Any]) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)

    min_val = schema.get("min_val")
    max_val = schema.get("max_val")
    if isinstance(min_val, (int, float)):
        number = max(float(min_val), number)
    if isinstance(max_val, (int, float)):
        number = min(float(max_val), number)
    return number


def _validate_number(value: Any, default: Any, schema: Mapping[str, Any]) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _validate_toggle(value: Any, default: Any, schema: Mapping[str, Any]) -> bool:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, bool):
        return value
    return bool(default)


def _validate_list(value: Any, default: Any, schema: Mapping[str, Any]) -> Any:
    options = schema.get("options", [])
    if not isinstance(options, list) or not options:
        return value if value is not None else default

    if value in options:
        return value
    if default in options:
        return default
    return options[0]


def _validate_button(value: Any, default: Any, schema: Mapping[str, Any]) -> bool:
    return _validate_toggle(value, default, schema)


def _validate_text(value: Any, default: Any, schema: Mapping[str, Any]) -> str:
    if value is None:
        return str(default)
    return str(value)


_VALIDATORS: Dict[ServiceParamType, Validator] = {
    ServiceParamType.SLIDER: _validate_slider,
    ServiceParamType.TOGGLE: _validate_toggle,
    ServiceParamType.LIST: _validate_list,
    ServiceParamType.BUTTON: _validate_button,
    ServiceParamType.NUMBER: _validate_number,
    ServiceParamType.TEXT: _validate_text,
}


def register_param_type_validator(param_type: ServiceParamType, validator: Validator) -> None:
    """Permet d'ajouter ou remplacer un validateur de type de parametre."""

    _VALIDATORS[param_type] = validator


def normalize_param_type(param_type: Any) -> ServiceParamType:
    """Convertit une valeur libre vers un type de parametre connu."""

    if isinstance(param_type, ServiceParamType):
        return param_type

    try:
        return ServiceParamType(str(param_type).strip().lower())
    except Exception as exc:
        allowed = ", ".join(t.value for t in ServiceParamType)
        raise ValueError(f"Type de parametre invalide: {param_type!r}. Types autorises: {allowed}") from exc


def coerce_param_value(param_type: Any, value: Any, default: Any, schema: Mapping[str, Any]) -> Any:
    """Nettoie/valide une valeur de parametre selon son type."""

    normalized = normalize_param_type(param_type)
    validator = _VALIDATORS[normalized]
    return validator(value, default, schema)

