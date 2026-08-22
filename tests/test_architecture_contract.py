import json
import os
import re
import unittest

from src.qt_bridge import DashboardBridge
from src.signal_catalog import SIGNALS


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ArchitectureContractTest(unittest.TestCase):
    def test_normal_shutdown_never_uses_os_exit(self):
        for relative in ("main.py", "src/qt_bridge.py"):
            with open(os.path.join(ROOT, relative), encoding="utf-8") as stream:
                self.assertNotIn("os._exit", stream.read())

    def test_every_bridge_reference_in_qml_exists_on_dashboard_bridge(self):
        meta = DashboardBridge.staticMetaObject
        exposed = {
            meta.property(index).name()
            for index in range(meta.propertyOffset(), meta.propertyCount())
        }
        exposed.update(
            bytes(meta.method(index).name()).decode("utf-8")
            for index in range(meta.methodOffset(), meta.methodCount())
        )
        references = set()
        frontend = os.path.join(ROOT, "frontend")
        for base, _dirs, files in os.walk(frontend):
            for filename in files:
                if filename.endswith(".qml"):
                    with open(os.path.join(base, filename), encoding="utf-8") as stream:
                        references.update(re.findall(r"\bbridge\.(\w+)", stream.read()))
        self.assertEqual(references - exposed, set())

    def test_every_decoded_can_signal_has_an_explicit_catalog_domain(self):
        path = os.path.join(ROOT, "data", "can", "can_moteur_clio3.json")
        with open(path, encoding="utf-8") as stream:
            database = json.load(stream)
        decoded_names = set()
        for frame_id, frame in database.items():
            if frame_id == "schema_version":
                continue
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

    def test_official_themes_only_use_theme_api_v1(self):
        styles = os.path.join(ROOT, "frontend", "styles")
        offenders = []
        for style_id in ("gt_modern", "apex", "atelier_luxe", "jdm_mugen", "legacy_dashboard"):
            dashboard = os.path.join(styles, style_id, "Dashboard.qml")
            with open(dashboard, encoding="utf-8") as stream:
                source = stream.read()
            for signal in ("settingsRequested", "commandRequested"):
                if not re.search(rf"\bsignal\s+{signal}\s*\(", source):
                    offenders.append(f"{style_id}: signal {signal} manquant")
            for base, _dirs, files in os.walk(os.path.join(styles, style_id)):
                for filename in files:
                    if not filename.endswith(".qml"):
                        continue
                    with open(os.path.join(base, filename), encoding="utf-8") as stream:
                        qml = stream.read()
                    if re.search(r"\bbridge\.", qml) or "shared_pages" in qml:
                        offenders.append(os.path.relpath(os.path.join(base, filename), ROOT))
        self.assertEqual(offenders, [])

    def test_every_official_theme_enters_the_shared_menu(self):
        styles = os.path.join(ROOT, "frontend", "styles")
        for style_id in ("gt_modern", "apex", "atelier_luxe", "jdm_mugen", "legacy_dashboard"):
            dashboard = os.path.join(styles, style_id, "Dashboard.qml")
            with open(dashboard, encoding="utf-8") as stream:
                source = stream.read()
            self.assertIn('settingsRequested("menu")', source, style_id)

        with open(os.path.join(ROOT, "frontend", "components", "SettingsShell.qml"), encoding="utf-8") as stream:
            settings_shell = stream.read()
        with open(os.path.join(ROOT, "frontend", "shared_pages", "MenuPage.qml"), encoding="utf-8") as stream:
            menu = stream.read()
        self.assertIn('menu: "../shared_pages/MenuPage.qml"', settings_shell)
        for action in ("reset_a", "reset_b", "pause_trip", "resume_trip", "end_trip"):
            self.assertIn(action, menu)

    def test_every_shared_detail_page_can_return_to_the_menu(self):
        pages = os.path.join(ROOT, "frontend", "shared_pages")
        for filename in ("AppearancePage.qml", "VehiclePage.qml", "ServicesPage.qml", "SystemPage.qml", "DiagnosticPage.qml", "DeveloperPage.qml"):
            with open(os.path.join(pages, filename), encoding="utf-8") as stream:
                source = stream.read()
            self.assertIn("signal backRequested()", source, filename)
            self.assertIn("PageHeader", source, filename)

    def test_jdm_needles_are_instantaneous_with_visual_motion_trails(self):
        components = os.path.join(ROOT, "frontend", "styles", "jdm_mugen", "components")
        for filename, direct_value in (("MugenTachometer.qml", "currentRpm / dialMaxRpm"), ("MugenSpeedometer.qml", "currentSpeed / dialMaxSpeed")):
            with open(os.path.join(components, filename), encoding="utf-8") as stream:
                source = stream.read()
            self.assertIn(direct_value, source, filename)
            self.assertIn("motionTrailOpacity", source, filename)
            self.assertNotIn("smoothRpm", source, filename)
            self.assertNotIn("smoothSpeed", source, filename)

        with open(os.path.join(components, "MugenCombimeter.qml"), encoding="utf-8") as stream:
            combimeter = stream.read()
        with open(os.path.join(components, "MugenClusterBezel.qml"), encoding="utf-8") as stream:
            bezel = stream.read()
        self.assertIn("auxiliaryGaugeOffset: 158", combimeter)
        self.assertIn("id: buttonFace", bezel)


if __name__ == "__main__":
    unittest.main()
