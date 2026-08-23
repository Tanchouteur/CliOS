import QtQuick
import "../style" as T

Item {
    id: root
    property string route: "home"
    signal backRequested()
    signal commandRequested(string command)
    signal navigateRequested(string route)

    readonly property var routeSources: ({
        menu: "../shared_pages/MenuPage.qml",
        appearance: "../shared_pages/AppearancePage.qml",
        vehicle: "../shared_pages/VehiclePage.qml",
        services: "../shared_pages/ServicesPage.qml",
        system: "../shared_pages/SystemPage.qml",
        diagnostic: "../shared_pages/DiagnosticPage.qml",
        developer: "../shared_pages/DeveloperPage.qml",
        leds: "../shared_pages/LedManagerPage.qml"
    })

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }

    Loader {
        id: pageLoader
        anchors.fill: parent
        source: root.routeSources[root.route] ? Qt.resolvedUrl(root.routeSources[root.route]) : ""
    }

    Connections {
        target: pageLoader.item
        ignoreUnknownSignals: true
        function onBackRequested() { root.backRequested() }
        function onNavigateRequested(route) {
            if (root.routeSources[route]) root.navigateRequested(route)
        }
        function onActionRequested(command) { root.commandRequested(command) }
    }

    Rectangle {
        anchors.centerIn: parent; width: 720; height: 210
        visible: pageLoader.status === Loader.Error || !root.routeSources[root.route]
        color: T.StyleManager.surface; radius: T.StyleManager.radiusLarge
        border.width: 2; border.color: T.StyleManager.danger
        Column {
            anchors.centerIn: parent; spacing: 16
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "PAGE INDISPONIBLE"; color: T.StyleManager.danger; font.pixelSize: 28; font.bold: true }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Route: " + root.route; color: T.StyleManager.textSecondary; font.pixelSize: 18 }
        }
    }
}
