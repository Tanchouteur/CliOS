from dataclasses import dataclass


@dataclass
class RawFrame:
    """Structure de données immuable représentant une trame CAN brute."""
    id: int
    data: bytearray
    timestamp: float


class SignalProcessor:
    """Moteur d'extraction et de conversion des signaux télémétriques.
    Isole la logique mathématique de décodage des payloads CAN.
    """

    def decode(self, frame: RawFrame, definition: dict) -> dict:
        """Décode le payload d'une trame CAN selon un dictionnaire de définition."""
        results = {}

        for sig_name, sig_def in definition.get("signals", {}).items():
            start = sig_def.get("start_byte", 0)

            # --- Traitement des champs de bits (États discrets / Booléens) ---
            if "bits" in sig_def:
                size = sig_def.get("size", 1)
                endian = sig_def.get("endian", "big")

                # Concaténation des octets pour permettre l'évaluation de masques sur plusieurs octets
                raw_bytes = frame.data[start: start + size]
                combined_bits = int.from_bytes(raw_bytes, byteorder=endian)

                for bit_name, bit_pos in sig_def["bits"].items():
                    # Extraction de l'état logique par décalage binaire et masquage (AND 1)
                    results[bit_name] = bool((combined_bits >> bit_pos) & 1)

            # --- Traitement des valeurs numériques (Signaux analogiques quantifiés) ---
            else:
                size = sig_def.get("size", 1)
                endian = sig_def.get("endian", "big")
                factor = sig_def.get("factor", 1.0)
                offset = sig_def.get("offset", 0.0)

                # Extraction de la séquence d'octets bruts
                raw_bytes = frame.data[start: start + size]
                raw_int = int.from_bytes(raw_bytes, byteorder=endian)

                # Application du masque binaire (Isolation du segment de données utile)
                if "mask" in sig_def:
                    mask_val = int(sig_def["mask"], 16)
                    raw_int = raw_int & mask_val

                # Alignement de la valeur par décalage de bits (Bitshift)
                if "shift" in sig_def:
                    raw_int = raw_int >> sig_def["shift"]

                # Application de la fonction de transfert linéaire (Mise à l'échelle)
                results[sig_name] = (raw_int * factor) + offset

        return results