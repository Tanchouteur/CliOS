import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 480
    height: 560

    // Transformation 3D GPU vers le centre (Cockpit Wraparound)
    transform: [
        Rotation {
            origin.x: 0
            origin.y: root.height / 2
            axis { x: 0; y: 1; z: 0 }
            angle: -8.5
        }
    ]

    // Cadran 3D Compte-tours Principal
    LuxeDial3D {
        id: dial
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 12
        width: 440
        height: 440
        minValue: 0
        maxValue: S.UiState.number(S.UiState.maxRpm, 7000)
        currentValue: S.UiState.rpm
        startAngle: 225
        spanAngle: 270
        majorStep: 1000
        minorTicksCount: 3
        redlineStartValue: S.UiState.number(S.UiState.redlineRpm, 6500)
        unitText: "TR/MIN"
        isRightDial: true
    }

    // Rapport Engagé Sculpté au centre du cadran (Épuré & Grand Format)
    Rectangle {
        anchors.centerIn: dial
        width: 90
        height: 90
        radius: 45
        color: "#080D15"
        border.width: 2.5
        border.color: S.UiState.redline ? T.StyleManager.warning : T.StyleManager.accent

        // Reflet interne zénithal
        Rectangle {
            anchors.fill: parent
            radius: 45
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.25)
        }

        Text {
            anchors.centerIn: parent
            text: S.UiState.gear
            color: S.UiState.redline ? T.StyleManager.warning : "#FFFFFF"
            font.family: T.StyleManager.fontFamily
            font.pixelSize: 48
            font.weight: Font.Bold
        }
    }

    // Bloc Inférieur Flottant : Consommation Instantanée & Température Moteur (Position surélevée sécurisée)
    RowLayout {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12

        // Consommation Instantanée
        Rectangle {
            Layout.fillWidth: true
            height: 64
            radius: 14
            color: "#0E1624"
            border.width: 1
            border.color: "#1C2A3C"

            Column {
                anchors.centerIn: parent
                spacing: 2
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "CONSO INSTANTANÉE"
                    color: "#BAC8D9"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.fixed(S.UiState.trip.inst_cons, 1, "0,0") + " L/100"
                    color: "#FFFFFF"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 17
                    font.weight: Font.Bold
                }
            }
        }

        // Température Eau Moteur
        Rectangle {
            Layout.fillWidth: true
            height: 64
            radius: 14
            color: "#0E1624"
            border.width: 1
            border.color: S.UiState.engineTemp >= 105 ? T.StyleManager.danger : "#1C2A3C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "EAU MOTEUR"
                        color: S.UiState.engineTemp >= 105 ? T.StyleManager.danger : "#BAC8D9"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: S.UiState.fixed(S.UiState.engineTemp, 0, "—") + " °C"
                        color: S.UiState.engineTemp >= 105 ? T.StyleManager.danger : "#FFFFFF"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 15
                        font.weight: Font.Bold
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 5
                    radius: 2.5
                    color: "#182436"

                    Rectangle {
                        width: parent.width * Math.min(1.0, Math.max(0.0, (S.UiState.engineTemp - 40) / (120 - 40)))
                        height: parent.height
                        radius: 2.5
                        color: S.UiState.engineTemp >= 105 ? T.StyleManager.danger : T.StyleManager.success
                        Behavior on width { NumberAnimation { duration: 200 } }
                    }
                }
            }
        }
    }
}
