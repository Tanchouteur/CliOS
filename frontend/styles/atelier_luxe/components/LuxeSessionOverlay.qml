import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Rectangle {
    id: root
    width: 1920
    height: 720
    anchors.fill: parent
    visible: S.UiState.sessionState === "PAUSED" || S.UiState.sessionState === "ENDED"
    color: "#E604060A" // 90% noir
    z: 900

    signal actionRequested(string action)

    Rectangle {
        anchors.centerIn: parent
        width: 860
        height: 420
        radius: 20
        color: "#0E1522"
        border.width: 2
        border.color: T.StyleManager.accent

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 20

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: S.UiState.sessionState === "ENDED" ? "TRAJET CLÔTURÉ" : "TRAJET EN PAUSE"
                color: "#FFFFFF"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 28
                font.weight: Font.Bold
                font.letterSpacing: 2
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(1, 1, 1, 0.08) }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 20

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "DISTANCE"; color: "#BAC8D9"; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripDistance, 1, "0,0") + " km"; color: "#FFFFFF"; font.pixelSize: 28; font.weight: Font.Bold }
                }

                Rectangle { width: 1; height: 50; color: Qt.rgba(1, 1, 1, 0.1) }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "CARBURANT"; color: "#BAC8D9"; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripFuelLiters, 2, "0,00") + " L"; color: "#FFFFFF"; font.pixelSize: 28; font.weight: Font.Bold }
                }

                Rectangle { width: 1; height: 50; color: Qt.rgba(1, 1, 1, 0.1) }

                Column {
                    Layout.fillWidth: true
                    spacing: 4
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: "COÛT ESTIMÉ"; color: "#BAC8D9"; font.pixelSize: 12; font.weight: Font.Bold; font.letterSpacing: 1.2 }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripCost, 2, "0,00") + " €"; color: T.StyleManager.accent; font.pixelSize: 28; font.weight: Font.Bold }
                }
            }

            Row {
                visible: S.UiState.sessionState === "PAUSED"
                Layout.alignment: Qt.AlignHCenter
                spacing: 20

                Rectangle {
                    width: 260; height: 58; radius: 12
                    color: touchResume.pressed ? Qt.darker(T.StyleManager.accent, 1.3) : T.StyleManager.accent
                    Text { anchors.centerIn: parent; text: "REPRENDRE"; color: "#000000"; font.pixelSize: 16; font.bold: true; font.letterSpacing: 1 }
                    MouseArea { id: touchResume; anchors.fill: parent; onClicked: root.actionRequested("resume_trip") }
                }

                Rectangle {
                    width: 260; height: 58; radius: 12
                    color: Qt.rgba(1.0, 0.3, 0.35, 0.18)
                    border.width: 2; border.color: T.StyleManager.danger
                    Text { anchors.centerIn: parent; text: "CLÔTURER LE TRAJET"; color: T.StyleManager.danger; font.pixelSize: 15; font.bold: true; font.letterSpacing: 1 }
                    MouseArea { anchors.fill: parent; onClicked: root.actionRequested("end_trip") }
                }
            }

            Text {
                visible: S.UiState.sessionState === "ENDED"
                Layout.alignment: Qt.AlignHCenter
                text: "Données de trajet enregistrées avec succès"
                color: T.StyleManager.success
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }
        }
    }
}
