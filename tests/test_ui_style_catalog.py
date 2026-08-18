import json
import os
import tempfile
import unittest

from src.qt_bridge import DashboardBridge


PALETTE = {
    "background": "#000000",
    "surface": "#111111",
    "surfaceRaised": "#222222",
    "surfaceSoft": "#333333",
    "text": "#FFFFFF",
    "textSecondary": "#DDDDDD",
    "outline": "#555555",
    "gaugeTrack": "#444444",
}


class UiStyleCatalogTest(unittest.TestCase):
    def make_bridge(self, styles_dir):
        bridge = DashboardBridge.__new__(DashboardBridge)
        bridge._ui_styles_dir = styles_dir
        bridge.logger = type("Logger", (), {"error": lambda *args, **kwargs: None})()
        return bridge

    def write_style(self, root, folder, manifest, with_dashboard=True):
        style_dir = os.path.join(root, folder)
        os.makedirs(style_dir)
        with open(os.path.join(style_dir, "style.json"), "w", encoding="utf-8") as stream:
            json.dump(manifest, stream)
        if with_dashboard:
            with open(os.path.join(style_dir, "Dashboard.qml"), "w", encoding="utf-8") as stream:
                stream.write("import QtQuick\nItem {}\n")

    def test_discovers_valid_packages_and_ignores_invalid_or_template(self):
        with tempfile.TemporaryDirectory() as styles_dir:
            self.write_style(styles_dir, "valid_style", {
                "id": "valid_style", "label": "Valide", "description": "Test",
                "order": 5, "dashboard": "Dashboard.qml", "palette": PALETTE,
            })
            self.write_style(styles_dir, "wrong_id", {
                "id": "another_id", "label": "Invalide", "dashboard": "Dashboard.qml",
                "palette": PALETTE,
            })
            self.write_style(styles_dir, "missing_qml", {
                "id": "missing_qml", "label": "Invalide", "dashboard": "Dashboard.qml",
                "palette": PALETTE,
            }, with_dashboard=False)
            self.write_style(styles_dir, "_template", {
                "id": "_template", "label": "Gabarit", "dashboard": "Dashboard.qml",
                "palette": PALETTE,
            })

            styles = DashboardBridge.getAvailableUiStyles(self.make_bridge(styles_dir))

            self.assertEqual([style["id"] for style in styles], ["valid_style"])
            self.assertEqual(styles[0]["dashboard"], "styles/valid_style/Dashboard.qml")


if __name__ == "__main__":
    unittest.main()
