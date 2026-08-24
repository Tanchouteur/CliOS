import QtQuick
import "../style" as T

Item {
    id: root
    signal settingsRequested(string route)
    signal commandRequested(string command)
    signal dashboardReady()

    Loader {
        id: loader
        anchors.fill: parent
        source: Qt.resolvedUrl("../" + T.StyleManager.dashboardSource)
        onLoaded: root.dashboardReady()
    }

    Connections {
        target: loader.item
        ignoreUnknownSignals: true
        function onSettingsRequested(route) { root.settingsRequested(route) }
        function onCommandRequested(command) { root.commandRequested(command) }
    }
}
