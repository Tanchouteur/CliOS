"""Catalogue persistant d'appareils et de groupes LED BLE.

Chaque appareil confirme est stocke dans le PersistentStorage de CliOS.
Les groupes permettent de piloter plusieurs appareils ensemble.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.logging_runtime import get_logger

logger = get_logger("BLE.DeviceCatalog")

PREDEFINED_NAMES: list[str] = [
    "Tableau de bord", "Plancher", "Portiere gauche", "Portiere droite",
    "Console centrale", "Coffre", "Ciel de toit", "Siege conducteur",
    "Siege passager", "Pedalier", "Boite a gants",
]

MAX_DEVICES: int = 4

DEFAULT_GROUP_ID: str = "all"
DEFAULT_GROUP_NAME: str = "Tout"


@dataclass
class BleDevice:
    """Appareil LED BLE confirme et configure."""

    id: str
    name: str
    ble_address: str
    protocol: str
    gatt_char_uuid: str
    write_with_response: bool
    advertised_name: str
    enabled: bool = True
    brightness: float = 100.0
    color_override: Optional[str] = None
    groups: list[str] = field(default_factory=lambda: [DEFAULT_GROUP_ID])
    last_seen: Optional[str] = None
    health: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ble_address": self.ble_address,
            "protocol": self.protocol,
            "gatt_char_uuid": self.gatt_char_uuid,
            "write_with_response": self.write_with_response,
            "advertised_name": self.advertised_name,
            "enabled": self.enabled,
            "brightness": self.brightness,
            "color_override": self.color_override,
            "groups": list(self.groups),
            "last_seen": self.last_seen,
            "health": self.health,
        }

    @staticmethod
    def from_dict(data: dict) -> "BleDevice":
        return BleDevice(
            id=str(data.get("id", "")),
            name=str(data.get("name", "Inconnu")),
            ble_address=str(data.get("ble_address", "")),
            protocol=str(data.get("protocol", "")),
            gatt_char_uuid=str(data.get("gatt_char_uuid", "")),
            write_with_response=bool(data.get("write_with_response", False)),
            advertised_name=str(data.get("advertised_name", "")),
            enabled=bool(data.get("enabled", True)),
            brightness=float(data.get("brightness", 100.0)),
            color_override=data.get("color_override") or None,
            groups=list(data.get("groups", [DEFAULT_GROUP_ID])),
            last_seen=data.get("last_seen"),
            health=str(data.get("health", "unknown")),
        )


@dataclass
class BleGroup:
    """Groupe d'appareils LED BLE."""

    id: str
    name: str
    color_override: Optional[str] = None
    enabled: bool = True
    brightness: float = 100.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color_override": self.color_override,
            "enabled": self.enabled,
            "brightness": self.brightness,
        }

    @staticmethod
    def from_dict(data: dict) -> "BleGroup":
        return BleGroup(
            id=str(data.get("id", "")),
            name=str(data.get("name", "Groupe")),
            color_override=data.get("color_override") or None,
            enabled=bool(data.get("enabled", True)),
            brightness=float(data.get("brightness", 100.0)),
        )


class DeviceCatalog:
    """Catalogue persistant d'appareils et de groupes LED BLE.

    Les appareils et groupes sont serialises dans PersistentStorage.
    Un groupe par defaut \"Tout\" est toujours present et ne peut pas etre supprime.
    """

    STORAGE_KEY_DEVICES = "services.Leds.devices"
    STORAGE_KEY_GROUPS = "services.Leds.groups"

    def __init__(self, storage):
        self._storage = storage
        self._devices: dict[str, BleDevice] = {}
        self._groups: dict[str, BleGroup] = {}
        self._load()
        self._ensure_default_group()
        self.migrate_legacy_params()

    # -------------------------------------------------------------------------
    # Chargement / sauvegarde
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        if not self._storage:
            return
        raw_devices = self._storage.get(self.STORAGE_KEY_DEVICES, [])

        if isinstance(raw_devices, list):
            for d in raw_devices:
                if isinstance(d, dict) and d.get("id"):
                    dev = BleDevice.from_dict(d)
                    self._devices[dev.id] = dev

        raw_groups = self._storage.get(self.STORAGE_KEY_GROUPS, [])
        if isinstance(raw_groups, list):
            for g in raw_groups:
                if isinstance(g, dict) and g.get("id"):
                    grp = BleGroup.from_dict(g)
                    self._groups[grp.id] = grp

    def _ensure_default_group(self) -> None:
        if DEFAULT_GROUP_ID not in self._groups:
            default_group = BleGroup(id=DEFAULT_GROUP_ID, name=DEFAULT_GROUP_NAME)
            self._groups[DEFAULT_GROUP_ID] = default_group
            self._save_groups()

    def _save_devices(self) -> None:
        if self._storage:
            self._storage.set(self.STORAGE_KEY_DEVICES, [d.to_dict() for d in self._devices.values()])

    def _save_groups(self) -> None:
        if self._storage:
            self._storage.set(self.STORAGE_KEY_GROUPS, [g.to_dict() for g in self._groups.values()])


    # -------------------------------------------------------------------------
    # Helpers internes
    # -------------------------------------------------------------------------

    @staticmethod
    def _generate_device_id() -> str:
        return "dev_" + uuid.uuid4().hex[:6]

    @staticmethod
    def _generate_group_id() -> str:
        return "grp_" + uuid.uuid4().hex[:6]

    # -------------------------------------------------------------------------
    # CRUD Appareils
    # -------------------------------------------------------------------------

    def list_devices(self) -> list[BleDevice]:
        """Retourne tous les appareils configures."""
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Optional[BleDevice]:
        """Retourne un appareil par son identifiant CliOS."""
        return self._devices.get(device_id)

    def add_device(self, device: BleDevice) -> str:
        """Ajoute un appareil au catalogue. Leve ValueError si la limite est atteinte."""
        if any(
            existing.ble_address.casefold() == device.ble_address.casefold()
            for existing in self._devices.values()
        ):
            raise ValueError("Cet appareil est deja configure.")
        if len(self._devices) >= MAX_DEVICES:
            raise ValueError(
                f"Limite de {MAX_DEVICES} appareils atteinte. Supprimez un appareil avant d'en ajouter un nouveau."
            )
        if not device.id:
            device = BleDevice(
                id=self._generate_device_id(),
                name=device.name,
                ble_address=device.ble_address,
                protocol=device.protocol,
                gatt_char_uuid=device.gatt_char_uuid,
                write_with_response=device.write_with_response,
                advertised_name=device.advertised_name,
                enabled=device.enabled,
                brightness=device.brightness,
                color_override=device.color_override,
                groups=device.groups if device.groups else [DEFAULT_GROUP_ID],
                last_seen=device.last_seen,
                health=device.health,
            )
        self._devices[device.id] = device
        self._save_devices()
        logger.info("Appareil ajoute: %s (%s)", device.name, device.id,
                    extra={"error_code": "LED_DEVICE_ADDED"})
        return device.id

    def update_device(self, device_id: str, **kwargs) -> bool:
        """Met a jour un ou plusieurs champs d'un appareil."""
        device = self._devices.get(device_id)
        if not device:
            return False
        allowed = {
            "name", "enabled", "brightness", "color_override",
            "groups", "last_seen", "health", "protocol", "gatt_char_uuid",
            "write_with_response",
        }
        updated = device.to_dict()
        for key, value in kwargs.items():
            if key in allowed:
                updated[key] = value
        self._devices[device_id] = BleDevice.from_dict(updated)
        self._save_devices()
        return True

    def remove_device(self, device_id: str) -> bool:
        """Supprime un appareil du catalogue."""
        if device_id not in self._devices:
            return False
        name = self._devices[device_id].name
        del self._devices[device_id]
        # Retire l'appareil des groupes
        for group in self._groups.values():
            pass  # Les groupes ne stockent pas les device IDs directement
        self._save_devices()
        logger.info("Appareil supprime: %s (%s)", name, device_id,
                    extra={"error_code": "LED_DEVICE_REMOVED"})
        return True

    def enabled_devices(self) -> list[BleDevice]:
        """Retourne uniquement les appareils actifs."""
        return [d for d in self._devices.values() if d.enabled]

    def update_device_health(self, device_id: str, health: str) -> None:
        """Met a jour l'etat de sante d'un appareil (connecte, deconnecte, erreur)."""
        device = self._devices.get(device_id)
        if device:
            updated = device.to_dict()
            updated["health"] = health
            if health == "connected":
                updated["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            self._devices[device_id] = BleDevice.from_dict(updated)
            self._save_devices()

    # -------------------------------------------------------------------------
    # CRUD Groupes
    # -------------------------------------------------------------------------

    def list_groups(self) -> list[BleGroup]:
        """Retourne tous les groupes."""
        return list(self._groups.values())

    def get_group(self, group_id: str) -> Optional[BleGroup]:
        """Retourne un groupe par son identifiant."""
        return self._groups.get(group_id)

    def add_group(self, name: str) -> str:
        """Cree un nouveau groupe et retourne son identifiant."""
        group_id = self._generate_group_id()
        group = BleGroup(id=group_id, name=name)
        self._groups[group_id] = group
        self._save_groups()
        return group_id

    def update_group(self, group_id: str, **kwargs) -> bool:
        """Met a jour un ou plusieurs champs d'un groupe."""
        group = self._groups.get(group_id)
        if not group:
            return False
        allowed = {"name", "color_override", "enabled", "brightness"}
        updated = group.to_dict()
        for key, value in kwargs.items():
            if key in allowed:
                updated[key] = value
        self._groups[group_id] = BleGroup.from_dict(updated)
        self._save_groups()
        return True

    def remove_group(self, group_id: str) -> bool:
        """Supprime un groupe. Le groupe par defaut ne peut pas etre supprime."""
        if group_id == DEFAULT_GROUP_ID:
            return False
        if group_id not in self._groups:
            return False
        del self._groups[group_id]
        # Retire ce groupe de tous les appareils
        for device in self._devices.values():
            if group_id in device.groups:
                updated = device.to_dict()
                updated["groups"] = [g for g in device.groups if g != group_id]
                if not updated["groups"]:
                    updated["groups"] = [DEFAULT_GROUP_ID]
                self._devices[device.id] = BleDevice.from_dict(updated)
        self._save_groups()
        self._save_devices()
        return True

    def add_device_to_group(self, device_id: str, group_id: str) -> None:
        """Ajoute un appareil dans un groupe."""
        device = self._devices.get(device_id)
        if not device or group_id not in self._groups:
            return
        if group_id not in device.groups:
            updated = device.to_dict()
            updated["groups"] = list(device.groups) + [group_id]
            self._devices[device_id] = BleDevice.from_dict(updated)
            self._save_devices()

    def remove_device_from_group(self, device_id: str, group_id: str) -> None:
        """Retire un appareil d'un groupe. Garde toujours le groupe par defaut."""
        if group_id == DEFAULT_GROUP_ID:
            return
        device = self._devices.get(device_id)
        if not device:
            return
        if group_id in device.groups:
            updated = device.to_dict()
            new_groups = [g for g in device.groups if g != group_id]
            if not new_groups:
                new_groups = [DEFAULT_GROUP_ID]
            updated["groups"] = new_groups
            self._devices[device_id] = BleDevice.from_dict(updated)
            self._save_devices()

    # -------------------------------------------------------------------------
    # Vues calculees pour le LED service
    # -------------------------------------------------------------------------

    def get_effective_color(self, device: BleDevice, accent_hex: str) -> str:
        """Retourne la couleur effective d'un appareil.

        Priorite: couleur propre de l'appareil > couleur du groupe > couleur d'accent.
        """
        if device.color_override:
            return device.color_override
        for group_id in device.groups:
            group = self._groups.get(group_id)
            if group and group.color_override:
                return group.color_override
        return accent_hex

    def get_effective_brightness(self, device: BleDevice) -> float:
        """Retourne la luminosite effective d'un appareil (0.0-100.0)."""
        brightness = max(0.0, min(100.0, device.brightness))
        groups = [self._groups[group_id] for group_id in device.groups if group_id in self._groups]
        if groups:
            brightness *= min(max(0.0, min(100.0, group.brightness)) for group in groups) / 100.0
        return brightness

    def is_effectively_enabled(self, device: BleDevice) -> bool:
        """Combine l'etat individuel avec celui de tous ses groupes."""
        if not device.enabled:
            return False
        return all(
            self._groups[group_id].enabled
            for group_id in device.groups
            if group_id in self._groups
        )

    # -------------------------------------------------------------------------
    # Serialisation pour le QML bridge
    # -------------------------------------------------------------------------

    def devices_to_json(self) -> list[dict]:
        """Retourne la liste des appareils serialisee pour QML."""
        return [d.to_dict() for d in self._devices.values()]

    def groups_to_json(self) -> list[dict]:
        """Retourne la liste des groupes serialisee pour QML."""
        result = []
        for g in self._groups.values():
            d = g.to_dict()
            # Ajoute le nombre d'appareils dans ce groupe
            d["device_count"] = sum(1 for dev in self._devices.values() if g.id in dev.groups)
            result.append(d)
        return result

    # -------------------------------------------------------------------------
    # Migration des anciens parametres
    # -------------------------------------------------------------------------

    def migrate_legacy_params(self) -> None:
        """Migration unique depuis les anciens parametres dash_*/foot_*.

        Si des appareils existent deja, la migration est ignoree.
        Les anciennes cles sont conservees pour permettre un rollback.
        """
        if self._devices:
            return  # Migration deja effectuee ou appareils deja configures

        if not self._storage:
            return  # Pas de storage, pas de migration possible

        legacy_prefix = "services.Leds.params."

        dash_mac = self._storage.get(legacy_prefix + "dash_mac", "")
        foot_mac = self._storage.get(legacy_prefix + "foot_mac", "")

        if not dash_mac and not foot_mac:
            return  # Aucune configuration legacy


        brightness = float(self._storage.get(legacy_prefix + "brightness", 100.0))

        if dash_mac:
            dash_device = BleDevice(
                id=self._generate_device_id(),
                name="Habitacle",
                ble_address=str(dash_mac),
                protocol=str(self._storage.get(legacy_prefix + "dash_proto", "LEDCAR_DMX_9B")),
                gatt_char_uuid="",
                write_with_response=False,
                advertised_name="",
                enabled=bool(self._storage.get(legacy_prefix + "dash_on", True)),
                brightness=brightness,
                groups=[DEFAULT_GROUP_ID],
            )
            self._devices[dash_device.id] = dash_device
            logger.info("Migration legacy: Habitacle cree depuis dash_mac",
                        extra={"error_code": "LED_MIGRATION"})

        if foot_mac and len(self._devices) < MAX_DEVICES:
            foot_device = BleDevice(
                id=self._generate_device_id(),
                name="Plancher",
                ble_address=str(foot_mac),
                protocol=str(self._storage.get(legacy_prefix + "foot_proto", "LOTUS_9B")),
                gatt_char_uuid="",
                write_with_response=False,
                advertised_name="",
                enabled=bool(self._storage.get(legacy_prefix + "foot_on", True)),
                brightness=brightness,
                groups=[DEFAULT_GROUP_ID],
            )
            self._devices[foot_device.id] = foot_device
            logger.info("Migration legacy: Plancher cree depuis foot_mac",
                        extra={"error_code": "LED_MIGRATION"})

        if self._devices:
            self._save_devices()
