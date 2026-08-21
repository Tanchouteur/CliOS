import QtQuick
import QtQuick.Layouts
import "../../style" as T
import "../../state" as S
import "./components"

Item {
    id: root
    width: 1920
    height: 720
    clip: true

    objectName: "mugenDashboardRoot"
    focus: true
    signal settingsRequested(string route)
    signal commandRequested(string command)

    // Propriétés d'état
    property string currentView: "drive" // "drive" ou nom de sous-page
    property string pendingAction: ""
    property string pendingTitle: ""
    property string pendingDescription: ""
    property bool pendingDangerous: false

    function navigate(viewId) {
        currentView = viewId
        if (viewId === "drive" || viewId === "cockpit" || viewId === "main") {
            subPageOverlay.visible = false
            subPageLoader.source = ""
        } else if (["appearance", "vehicle", "services", "system", "diagnostic", "developer"].indexOf(viewId) >= 0) {
            root.settingsRequested(viewId)
        }
    }

    function askConfirmation(action) {
        root.commandRequested(action)
    }

    function executeConfirmed() {
        confirmDialog.close()
        root.commandRequested(pendingAction)
        pendingAction = ""
    }

    // Gestion des touches raccourcis
    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_T) {
            root.commandRequested(S.UiState.sessionState === "PAUSED" ? "resume_trip" : "pause_trip")
            event.accepted = true
        } else if (event.key === Qt.Key_M) {
            menuDrawer.open()
            event.accepted = true
        }
    }

    // =========================================================================
    // 0. ARRIÈRE-PLAN NOIR AUTOMOBILE
    // =========================================================================
    Rectangle {
        anchors.fill: parent
        color: "#070A0E"
        z: 0
    }

    // =========================================================================
    // 1. CASQUETTE DE COMBINÉ & CADRE AUTOMOBILE (Arrière-plan & Telltales)
    // =========================================================================
    MugenClusterBezel {
        id: clusterBezel
        z: 40
        onOpenMenuRequested: menuDrawer.open()
        onActionRequested: (action) => root.askConfirmation(action)
    }

    // =========================================================================
    // 2. DISPOSITION DES 3 CADRANS BLANCS MUGEN (Vue Conduite Principale)
    // =========================================================================
    Item {
        id: clusterGauges
        anchors.fill: parent
        z: 20

        // --- Cadran Gauche : Compte-tours Mugen (0 à 9000 tr/min + Trip LCD) ---
        MugenTachometer {
            id: tachometer
            x: 170
            y: 140
            width: 480
            height: 480
        }

        // --- Cadran Droit : Combiné Essence + Eau + Rapports PRND + Range LCD ---
        MugenCombimeter {
            id: combimeter
            x: 1270
            y: 140
            width: 480
            height: 480
        }

        // --- Cadran Central : Compteur de Vitesse Agrandie (0 à 220 km/h + Logo Mugen) ---
        MugenSpeedometer {
            id: speedometer
            x: 685
            y: 95
            width: 550
            height: 550
            z: 25 // Légèrement au premier plan
        }
    }

    // =========================================================================
    // 3. OVERLAY DES SOUS-PAGES PARTAGÉES (Apparence, Véhicule, Services, etc.)
    // =========================================================================
    Rectangle {
        id: subPageOverlay
        anchors.fill: parent
        color: T.StyleManager.background
        visible: false
        z: 500

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // Barre supérieure de navigation sous-pages avec bouton de retour
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                color: "#0B1017"
                border.width: 1
                border.color: "#1E2A3A"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    spacing: 16

                    // Bouton Retour Cockpit Mugen
                    Rectangle {
                        Layout.preferredWidth: 260
                        Layout.preferredHeight: 38
                        radius: 8
                        color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.2)
                        border.width: 1.2
                        border.color: T.StyleManager.accent

                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Text { text: "◀"; color: T.StyleManager.accent; font.pixelSize: 14; font.bold: true }
                            Text { text: "RETOUR AU COMBINÉ"; color: "#FFFFFF"; font.pixelSize: 12; font.bold: true; font.letterSpacing: 1.0 }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.navigate("drive")
                        }
                    }

                    // Bouton Menu
                    Rectangle {
                        Layout.preferredWidth: 140
                        Layout.preferredHeight: 38
                        radius: 8
                        color: "#141C28"
                        border.width: 1
                        border.color: "#28374B"

                        Row {
                            anchors.centerIn: parent
                            spacing: 6
                            Text { text: "☰"; color: "#FFFFFF"; font.pixelSize: 14 }
                            Text { text: "MENU"; color: "#BAC8D9"; font.pixelSize: 12; font.bold: true }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: menuDrawer.open()
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Text {
                        text: "CliOS MUGEN POWER"
                        color: T.StyleManager.accent
                        font.family: "Arial, sans-serif"
                        font.pixelSize: 15
                        font.weight: Font.Bold
                        font.letterSpacing: 1.5
                    }
                }
            }

            // Chargeur de la page partagée sélectionnée
            Loader {
                id: subPageLoader
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }

        Connections {
            target: subPageLoader.item
            ignoreUnknownSignals: true
            function onBackRequested() { root.navigate("drive") }
            function onNavigateRequested(target) { root.navigate(target) }
            function onActionRequested(action) { root.askConfirmation(action) }
        }
    }

    // =========================================================================
    // 4. MENU TIROIR TACTILE FLOTTANT ("un bouton en plus pour le menu qui mène vers tout le reste")
    // =========================================================================
    MugenMenuDrawer {
        id: menuDrawer
        z: 800
        onNavigateRequested: (target) => root.navigate(target)
        onActionRequested: (action) => root.askConfirmation(action)
    }

    // =========================================================================
    // 5. OVERLAY DE SESSION (Pause / Fin de Trajet)
    // =========================================================================
    MugenSessionOverlay {
        id: sessionOverlay
        z: 900
        onActionRequested: (action) => root.askConfirmation(action)
    }

    // =========================================================================
    // 6. DIALOGUE UNIVERSEL DE CONFIRMATION D'ACTION
    // =========================================================================
    MugenConfirmDialog {
        id: confirmDialog
        z: 1000
        onAccepted: root.executeConfirmed()
        onRejected: {
            confirmDialog.close()
            root.pendingAction = ""
        }
    }
}
