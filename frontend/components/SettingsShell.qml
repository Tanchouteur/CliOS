import QtQuick
import QtQuick.Layouts
import "../style" as T
import "../state" as S

Item {
    id: root
    objectName: "unifiedSettingsShell"
    property string route: "driving"
    property string requestedRoute: "driving"
    signal cockpitRequested()
    signal commandRequested(string command)
    signal navigateRequested(string route)
    signal styleRequested(string styleId)
    readonly property var sections: [
        { id: "driving", label: "Conduite", detail: "Trajets" },
        { id: "appearance", label: "Apparence", detail: "Styles et lumière" },
        { id: "vehicle", label: "Véhicule", detail: "Entretien et OBD" },
        { id: "system", label: "Système", detail: "Réseau et stockage" },
        { id: "advanced", label: "Avancé", detail: "Profils et services", secondary: true }
    ]
    readonly property var routeSources: ({
        menu: "../shared_pages/MenuPage.qml",
        driving: "../shared_pages/DrivingPage.qml", appearance: "../shared_pages/AppearancePage.qml",
        vehicle: "../shared_pages/VehiclePage.qml", system: "../shared_pages/SystemPage.qml",
        advanced: "../shared_pages/AdvancedPage.qml"
    })

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }
    Rectangle {
        id: rail
        objectName: "settingsNavigationRail"
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
        width: 288; color: T.StyleManager.surface
        border.width: 1; border.color: T.StyleManager.outline
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 16; spacing: 10
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 72
                radius: T.StyleManager.radiusMedium; color: cockpitTouch.pressed ? T.StyleManager.accentSoft : T.StyleManager.surfaceRaised
                border.width: 2; border.color: T.StyleManager.accent
                Text { anchors.centerIn: parent; text: "‹  COCKPIT"; color: T.StyleManager.text; font.pixelSize: 20; font.bold: true }
                MouseArea { id: cockpitTouch; anchors.fill: parent; onClicked: root.cockpitRequested() }
            }
            Text { text: "RÉGLAGES"; color: T.StyleManager.textSecondary; font.pixelSize: 13; font.bold: true; font.letterSpacing: 2; Layout.topMargin: 8 }
            Repeater {
                model: root.sections
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 76
                    radius: T.StyleManager.radiusSmall
                    color: root.route === modelData.id ? T.StyleManager.accentSoft : (navTouch.pressed ? T.StyleManager.surfaceRaised : "transparent")
                    border.width: root.route === modelData.id ? 2 : 1
                    border.color: root.route === modelData.id ? T.StyleManager.accent : "transparent"
                    opacity: modelData.secondary ? 0.76 : 1.0
                    Column { anchors.left: parent.left; anchors.leftMargin: 18; anchors.verticalCenter: parent.verticalCenter; spacing: 3
                        Text { text: modelData.label; color: T.StyleManager.text; font.pixelSize: 20; font.bold: true }
                        Text { text: modelData.detail; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
                    }
                    MouseArea { id: navTouch; anchors.fill: parent; onClicked: root.navigateRequested(modelData.id) }
                }
            }
            Item { Layout.fillHeight: true }
            Text { Layout.fillWidth: true; text: S.UiState.profileName(); color: T.StyleManager.text; font.pixelSize: 15; elide: Text.ElideRight }
            Text { Layout.fillWidth: true; text: "CliOS " + S.UiState.systemVersion; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
        }
    }
    Loader {
        id: pageLoader
        anchors.left: rail.right; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom
        source: root.routeSources[root.route] ? Qt.resolvedUrl(root.routeSources[root.route]) : ""
        onLoaded: if (item && item.initialRoute !== undefined) item.initialRoute = root.requestedRoute
    }
    Connections {
        target: pageLoader.item; ignoreUnknownSignals: true
        function onActionRequested(command) { root.commandRequested(command) }
        function onNavigateRequested(route) { root.navigateRequested(route) }
        function onStyleRequested(styleId) { root.styleRequested(styleId) }
    }
}
