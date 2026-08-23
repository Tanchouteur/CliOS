import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()
    signal navigateRequested(string route)
    signal actionRequested(string action)

    readonly property var sections: [
        { id: "appearance", number: "02", label: "APPARENCE", sub: "Thème, ambiance et couleurs du cockpit" },
        { id: "vehicle", number: "03", label: "VÉHICULE", sub: "Profil actif, capteurs et étalonnage" },
        { id: "diagnostic", number: "04", label: "DIAGNOSTIC", sub: "Codes défaut et état des calculateurs" },
        { id: "services", number: "05", label: "SERVICES", sub: "Modules et fonctions embarquées" },
        { id: "system", number: "06", label: "SYSTÈME", sub: "Stockage, mises à jour et alimentation" },
        { id: "leds", number: "07", label: "ÉCLAIRAGES", sub: "Bandeaux LED Bluetooth, scan et groupes" }
    ]

    Rectangle { anchors.fill: parent; color: T.StyleManager.background }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            color: T.StyleManager.surfaceRaised
            border.width: T.StyleManager.borderWidth
            border.color: T.StyleManager.outline

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 22
                spacing: 16

                Button {
                    Layout.preferredWidth: 190
                    Layout.preferredHeight: 48
                    text: "‹ COCKPIT"
                    primary: true
                    onClicked: root.backRequested()
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    Text { text: "MENU CLIOS"; color: T.StyleManager.text; font.pixelSize: 23; font.bold: true; font.letterSpacing: 2.0 }
                    Text { text: "Toutes les commandes dans un seul espace"; color: T.StyleManager.textSecondary; font.pixelSize: 13 }
                }
                Text {
                    text: S.UiState.usbConnected ? "USB" : (S.UiState.internalStorage ? "CARTE SD" : "MODE RAM")
                    color: S.UiState.ramMode ? T.StyleManager.warning : T.StyleManager.success
                    font.pixelSize: 14; font.bold: true
                }
                Button {
                    Layout.preferredWidth: 190
                    Layout.preferredHeight: 48
                    text: "DÉVELOPPEUR"
                    subtext: "CAN et outils avancés"
                    onClicked: root.navigateRequested("developer")
                }
                Text { text: "CliOS " + S.UiState.systemVersion; color: T.StyleManager.textSecondary; font.pixelSize: 14 }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 14
            columns: 3
            rowSpacing: 14
            columnSpacing: 14

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: T.StyleManager.surfaceRaised
                radius: T.StyleManager.radiusLarge
                border.width: 2
                border.color: T.StyleManager.accent

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 9

                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "01"; color: T.StyleManager.accent; font.pixelSize: 13; font.bold: true; font.letterSpacing: 2 }
                        Text { text: "TRAJETS"; color: T.StyleManager.text; font.pixelSize: 23; font.bold: true; font.letterSpacing: 2 }
                        Item { Layout.fillWidth: true }
                        Text { text: S.UiState.sessionState; color: S.UiState.tripActive ? T.StyleManager.success : T.StyleManager.textSecondary; font.pixelSize: 12; font.bold: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 66; radius: T.StyleManager.radiusSmall
                            color: T.StyleManager.surface; border.width: 1; border.color: T.StyleManager.outline
                            Column { anchors.centerIn: parent; spacing: 2
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "TRIP A"; color: T.StyleManager.textSecondary; font.pixelSize: 11; font.bold: true }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripA, 1, "0,0") + " km"; color: T.StyleManager.text; font.pixelSize: 21; font.bold: true }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 66; radius: T.StyleManager.radiusSmall
                            color: T.StyleManager.surface; border.width: 1; border.color: T.StyleManager.outline
                            Column { anchors.centerIn: parent; spacing: 2
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: "TRIP B"; color: T.StyleManager.textSecondary; font.pixelSize: 11; font.bold: true }
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripB, 1, "0,0") + " km"; color: T.StyleManager.text; font.pixelSize: 21; font.bold: true }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 8
                        Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "RESET A"; destructive: true; onClicked: root.actionRequested("reset_a") }
                        Button { Layout.fillWidth: true; Layout.fillHeight: true; text: "RESET B"; destructive: true; onClicked: root.actionRequested("reset_b") }
                        Button {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            text: S.UiState.sessionState === "PAUSED" ? "REPRENDRE" : "PAUSE"
                            enabled: S.UiState.tripActive || S.UiState.sessionState === "PAUSED"
                            onClicked: root.actionRequested(S.UiState.sessionState === "PAUSED" ? "resume_trip" : "pause_trip")
                        }
                        Button {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            text: "TERMINER"; destructive: true
                            enabled: S.UiState.tripActive || S.UiState.sessionState === "PAUSED"
                            onClicked: root.actionRequested("end_trip")
                        }
                    }
                }
            }

            Repeater {
                model: root.sections
                delegate: Rectangle {
                    id: menuCard
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: cardTouch.pressed ? T.StyleManager.accentSoft : T.StyleManager.surface
                    radius: T.StyleManager.radiusLarge
                    border.width: T.StyleManager.borderWidth
                    border.color: cardTouch.containsMouse ? T.StyleManager.accent : T.StyleManager.outline
                    scale: cardTouch.pressed ? 0.988 : 1.0
                    Behavior on scale { NumberAnimation { duration: T.StyleManager.durationFast } }

                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 22
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - 108
                        spacing: 10
                        Text { text: modelData.number; color: T.StyleManager.accent; font.pixelSize: 13; font.bold: true; font.letterSpacing: 2 }
                        Text { text: modelData.label; color: T.StyleManager.text; font.pixelSize: 23; font.bold: true; font.letterSpacing: 2 }
                        Text { width: parent.width; text: modelData.sub; color: T.StyleManager.textSecondary; font.pixelSize: 14; wrapMode: Text.WordWrap }
                    }
                    Rectangle {
                        anchors.right: parent.right
                        anchors.rightMargin: 22
                        anchors.verticalCenter: parent.verticalCenter
                        width: 54; height: 54; radius: T.StyleManager.radiusMedium
                        color: T.StyleManager.surfaceRaised
                        border.width: 1; border.color: T.StyleManager.outline
                        Text { anchors.centerIn: parent; text: "›"; color: T.StyleManager.text; font.pixelSize: 34; font.weight: Font.Light }
                    }
                    MouseArea {
                        id: cardTouch
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.navigateRequested(modelData.id)
                    }
                }
            }
        }
    }
}
