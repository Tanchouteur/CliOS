pragma Singleton
import QtQuick

QtObject {
    // Alias conservés pour les écrans secondaires historiques encore chargés.
    readonly property color bgMain: StyleManager.background
    readonly property color bgDimmed: StyleManager.surface
    readonly property color textMain: StyleManager.text
    readonly property color textDimmed: StyleManager.textSecondary
    readonly property color unselected: StyleManager.textSecondary
    readonly property color danger: StyleManager.danger
    readonly property color success: StyleManager.success
    readonly property color info: StyleManager.info
    readonly property color warning: StyleManager.warning
    property color main: StyleManager.accent
    readonly property color mainLight: Qt.lighter(main, 1.15)
    readonly property color mainDark: Qt.darker(main, 1.25)
    readonly property color secondary: StyleManager.info
    readonly property color secondaryLight: Qt.lighter(secondary, 1.15)
    readonly property color secondaryDark: Qt.darker(secondary, 1.25)
    readonly property color redLine: StyleManager.danger
    readonly property string fontMain: StyleManager.fontFamily
    readonly property string fontMono: Qt.platform.os === "osx" ? "Menlo" : (Qt.platform.os === "windows" ? "Consolas" : "DejaVu Sans Mono")
}
