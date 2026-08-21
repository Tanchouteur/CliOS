import QtQuick
import QtQuick.Layouts
import "../style" as T
import "../state" as S

Item {
    id: root
    property string route: "home"
    signal backRequested()
    signal commandRequested(string command)
    signal navigateRequested(string route)

    readonly property var routeSources: ({
        appearance: "../shared_pages/AppearancePage.qml",
        vehicle: "../shared_pages/VehiclePage.qml",
        services: "../shared_pages/ServicesPage.qml",
        system: "../shared_pages/SystemPage.qml",
        diagnostic: "../shared_pages/DiagnosticPage.qml",
        developer: "../shared_pages/DeveloperPage.qml"
    })

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }

    Rectangle {
        id: systemBar
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        height: 48
        color: T.StyleManager.surfaceRaised
        border.width: 1; border.color: T.StyleManager.outline
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 18; spacing: 14
            Rectangle {
                width: 130; height: 38; radius: T.StyleManager.radiusSmall
                color: backArea.pressed ? T.StyleManager.accentSoft : T.StyleManager.surface
                border.width: 1; border.color: T.StyleManager.outline
                Text { anchors.centerIn: parent; text: "‹ COCKPIT"; color: T.StyleManager.text; font.pixelSize: 16; font.bold: true }
                MouseArea { id: backArea; anchors.fill: parent; onClicked: root.backRequested() }
            }
            Text { text: "RÉGLAGES · " + root.route.toUpperCase(); color: T.StyleManager.text; font.pixelSize: 18; font.bold: true }
            Repeater {
                model: ["appearance", "vehicle", "services", "system", "diagnostic", "developer"]
                Rectangle {
                    width: 122; height: 34; radius: T.StyleManager.radiusSmall
                    color: root.route === modelData ? T.StyleManager.accentSoft : T.StyleManager.surface
                    border.width: 1; border.color: root.route === modelData ? T.StyleManager.accent : T.StyleManager.outline
                    Text { anchors.centerIn: parent; text: String(modelData).toUpperCase(); color: T.StyleManager.text; font.pixelSize: 11; font.bold: true }
                    MouseArea { anchors.fill: parent; onClicked: root.navigateRequested(String(modelData)) }
                }
            }
            Item { Layout.fillWidth: true }
            Text { text: S.UiState.storageMode; color: S.UiState.ramMode ? T.StyleManager.warning : T.StyleManager.success; font.pixelSize: 15; font.bold: true }
            Text { text: "CliOS " + S.UiState.systemVersion; color: T.StyleManager.textSecondary; font.pixelSize: 15 }
        }
    }

    Loader {
        id: pageLoader
        anchors.left: parent.left; anchors.right: parent.right
        anchors.top: systemBar.bottom; anchors.bottom: parent.bottom
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
