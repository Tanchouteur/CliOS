import json
import os
import re
import unittest

from src.qt_bridge import DashboardBridge
from src.signal_catalog import SIGNALS


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ArchitectureContractTest(unittest.TestCase):
    def test_every_decoded_can_signal_has_an_explicit_catalog_domain(self):
        path = os.path.join(ROOT, "data", "can", "can_moteur_clio3.json")
        with open(path, encoding="utf-8") as stream:
            database = json.load(stream)
        decoded_names = set()
        for frame in database.values():
            for name, signal in frame["signals"].items():
                decoded_names.update(signal.get("bits", {name: None}).keys())
        self.assertEqual(decoded_names - SIGNALS.keys(), set())
        self.assertNotIn("misc", {definition.domain for definition in SIGNALS.values()})

    def test_bridge_exposes_only_structured_state_properties(self):
        meta = DashboardBridge.staticMetaObject
        properties = {
            meta.property(index).name()
            for index in range(meta.propertyOffset(), meta.propertyCount())
        }
        expected = {
            "vehicleState", "tripState", "diagnosticsState", "systemState",
            "sessionState", "calibrationState", "presentationState",
            "dataQuality", "config",
        }
        self.assertEqual(properties, expected)
        self.assertTrue({"data", "stats", "systemHealth", "storageStatus"}.isdisjoint(properties))

    def test_qml_never_reads_removed_bridge_maps_or_flat_ui_maps(self):
        forbidden = re.compile(
            r"bridge\.(?:data|stats|systemHealth|storageStatus|diagnosticCodes|isScanning|hasScanned)\b"
            r"|S\.UiState\.(?:vehicle|trip|health)\b"
        )
        offenders = []
        frontend = os.path.join(ROOT, "frontend")
        for base, _dirs, files in os.walk(frontend):
            for filename in files:
                if not filename.endswith(".qml"):
                    continue
                path = os.path.join(base, filename)
                with open(path, encoding="utf-8") as stream:
                    for line_number, line in enumerate(stream, 1):
                        if forbidden.search(line):
                            offenders.append(f"{os.path.relpath(path, ROOT)}:{line_number}")
        self.assertEqual(offenders, [])

    def test_every_dashboard_ui_state_reference_is_declared(self):
        ui_state_path = os.path.join(ROOT, "frontend", "state", "UiState.qml")
        with open(ui_state_path, encoding="utf-8") as stream:
            ui_state = stream.read()
        declared = set(re.findall(
            r"\b(?:readonly\s+)?property\s+\w+\s+(\w+)", ui_state
        ))
        declared.update(re.findall(r"\bfunction\s+(\w+)", ui_state))

        missing = []
        styles = os.path.join(ROOT, "frontend", "styles")
        for base, _dirs, files in os.walk(styles):
            for filename in files:
                if not filename.endswith(".qml"):
                    continue
                path = os.path.join(base, filename)
                with open(path, encoding="utf-8") as stream:
                    source = stream.read()
                for reference in re.findall(r"(?:S\.)?UiState\.(\w+)", source):
                    if reference not in declared:
                        missing.append(f"{os.path.relpath(path, ROOT)}:{reference}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
