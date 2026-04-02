pragma Singleton
import QtQuick

QtObject {
    // --- Couleurs de Base (Fonds et Textes) ---
    readonly property color bgMain: "#0e0e10"
    readonly property color bgDimmed: "#1a1a1c"

    readonly property color textMain: "#f1eeee"
    readonly property color textDimmed: "#aaFFFFFF"
    readonly property color unselected: "#888888"

    // --- Couleurs d'Alerte (Voyants) ---
    readonly property color danger: "#e74c3c"
    readonly property color success: "#2ecc71"
    readonly property color info: "#3498db"
    readonly property color warning: "#e67e22"

    // --- Thème Dynamique (Couleur d'accentuation pour les LEDs) ---
    // property color accent: bridge.data.theme_color !== undefined ? bridge.data.theme_color : "#00aaff"
    property color main: "#ff4400"
    property color mainLight: "#ff6600"
    property color mainDark: "#cc3700"

    property color secondary: "#00aaff"
    property color secondaryLight: "#33bbff"
    property color secondaryDark: "#0088cc"

    property color redLine: "#ff1e00"
}