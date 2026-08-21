import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    anchors.fill: parent
    visible: S.UiState.sessionState === "PAUSED" || S.UiState.sessionState === "ENDED"

    signal actionRequested(string action)

    Rectangle {
        anchors.fill: parent
        color: "#E605080C"
    }

    Rectangle {
        width: 860
        height: 380
        anchors.centerIn: parent
        radius: 18
        color: "#0F151E"
        border.width: 2
        border.color: T.StyleManager.accent

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 28
            spacing: 20

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: S.UiState.sessionState === "ENDED" ? "TRAJET TERMINÉ" : "SESSION EN PAUSE"
                color: "#FFFFFF"
                font.family: "Arial, sans-serif"
                font.pixelSize: 22
                font.weight: Font.Bold
                font.letterSpacing: 1.5
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 24

                Rectangle {
                    Layout.fillWidth: true; height: 110; radius: 12; color: "#0A0D14"; border.width: 1; border.color: "#1C2737"
                    Column {
                        anchors.centerIn: parent; spacing: 4
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "DISTANCE"; color: "#8FA3B8"; font.pixelSize: 12; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripDistance, 1, "0.0") + " km"; color: "#FFFFFF"; font.pixelSize: 28; font.bold: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 110; radius: 12; color: "#0A0D14"; border.width: 1; border.color: "#1C2737"
                    Column {
                        anchors.centerIn: parent; spacing: 4
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "CARBURANT"; color: "#8FA3B8"; font.pixelSize: 12; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripFuelLiters, 2, "0.00") + " L"; color: "#FFFFFF"; font.pixelSize: 28; font.bold: true }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 110; radius: 12; color: "#0A0D14"; border.width: 1; border.color: "#1C2737"
                    Column {
                        anchors.centerIn: parent; spacing: 4
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "COÛT TRAJET"; color: "#8FA3B8"; font.pixelSize: 12; font.bold: true }
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: S.UiState.fixed(S.UiState.tripCost, 2, "0.00") + " €"; color: T.StyleManager.accent; font.pixelSize: 28; font.bold: true }
                    }
                }
            }

            Row {
                visible: S.UiState.sessionState === "PAUSED"
                Layout.alignment: Qt.AlignHCenter
                spacing: 20

                Rectangle {
                    width: 260; height: 50; radius: 10
                    color: T.StyleManager.accent
                    Text { anchors.centerIn: parent; text: "CONTINUER LE TRAJET"; color: "#000000"; font.pixelSize: 14; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.actionRequested("resume_trip") }
                }

                Rectangle {
                    width: 260; height: 50; radius: 10
                    color: Qt.rgba(T.StyleManager.danger.r, T.StyleManager.danger.g, T.StyleManager.danger.b, 0.2)
                    border.width: 1.5; border.color: T.StyleManager.danger
                    Text { anchors.centerIn: parent; text: "CLÔTURER LA SESSION"; color: T.StyleManager.danger; font.pixelSize: 14; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.actionRequested("end_trip") }
                }
            }

            Text {
                visible: S.UiState.sessionState === "ENDED"
                Layout.alignment: Qt.AlignHCenter
                text: "Données de trajet enregistrées avec succès."
                color: T.StyleManager.success
                font.pixelSize: 16
                font.weight: Font.DemiBold
            }
        }
    }
}
