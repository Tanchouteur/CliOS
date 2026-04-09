pragma Singleton
import QtQuick

QtObject {
    // --- Couleurs de Base  ---
    readonly property color bgMain: "#000000"
    readonly property color bgDimmed: "#1a1a1c"

    readonly property color textMain: "#f4f4f4"
    readonly property color textDimmed: "#aaFFFFFF"
    readonly property color unselected: "#888888"

    // --- Couleurs d'Alerte (Voyants) ---
    readonly property color danger: "#e73c3c"
    readonly property color success: "#2ecc71"
    readonly property color info: "#3498db"
    readonly property color warning: "#e67e22"

    // --- Thème Dynamique (Couleur d'accentuation pour les LEDs) ---
    property color main: bridge.config.theme.main !== undefined ? bridge.config.theme.main : "#00aaff"
    property color mainLight: Qt.lighter(main, 1.3)
    property color mainDark: Qt.darker(main, 1.4)

    property color secondary: "#00aaff"
    property color secondaryLight: "#33bbff"
    property color secondaryDark: "#0088cc"

    property color redLine: "#ff1e00"

    readonly property string fontMain: "sans-serif"

    readonly property string fontMono: "Courier"
}