import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 480
    height: 560

    // Transformation 3D GPU vers le centre (Cockpit Wraparound)
    transform: [
        Rotation {
            origin.x: root.width
            origin.y: root.height / 2
            axis { x: 0; y: 1; z: 0 }
            angle: 8.5
        }
    ]

    // Cadran 3D Tachymétrique Principal
    LuxeDial3D {
        id: dial
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 12
        width: 440
        height: 440
        minValue: 0
        maxValue: S.UiState.number(S.UiState.maxSpeed, 250)
        currentValue: S.UiState.speed
        startAngle: 225
        spanAngle: 270
        majorStep: 50
        minorTicksCount: 4
        unitText: "KM / H"
    }

    // Indicateur Régulateur / Limiteur intégré DIRECTEMENT au cadran
    Rectangle {
        anchors.horizontalCenter: dial.horizontalCenter
        anchors.bottom: centerHub.top
        anchors.bottomMargin: 14
        width: 130
        height: 28
        radius: 14
        visible: S.UiState.cruiseStatus === "ACTIF" || S.UiState.vehicle.regulateur_statut > 0
        color: S.UiState.cruiseStatus === "ACTIF" ? Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.22) : "#080D15"
        border.width: 1.2
        border.color: S.UiState.cruiseStatus === "ACTIF" ? T.StyleManager.accent : "#2A3C52"

        RowLayout {
            anchors.centerIn: parent
            spacing: 6
            Rectangle {
                width: 7; height: 7; radius: 3.5
                color: S.UiState.cruiseStatus === "ACTIF" ? T.StyleManager.accent : "#8A9BAF"
            }
            Text {
                text: S.UiState.cruiseMode + " " + S.UiState.fixed(S.UiState.cruiseTarget, 0, "—") + " km/h"
                color: S.UiState.cruiseStatus === "ACTIF" ? "#FFFFFF" : "#BAC8D9"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 0.8
            }
        }
    }

    // Affichage Vitesse Numérique dans un Cocon Central Sculpté
    Rectangle {
        id: centerHub
        anchors.centerIn: dial
        width: 90
        height: 90
        radius: 45
        color: "#080D15"
        border.width: 2.5
        border.color: T.StyleManager.accent

        // Reflet interne zénithal
        Rectangle {
            anchors.fill: parent
            radius: 45
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.25)
        }

        Column {
            anchors.centerIn: parent
            spacing: 0

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Math.round(S.UiState.speed).toString()
                color: "#FFFFFF"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 42
                font.weight: Font.Bold
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "KM / H"
                color: "#BAC8D9"
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 11
                font.weight: Font.Bold
                font.letterSpacing: 1.2
            }
        }
    }

    // Bloc Inférieur Flottant : Pédale d'Accélérateur & Odomètre
    RowLayout {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 12

        // Jauge Position Pédale Accélérateur
        Rectangle {
            Layout.fillWidth: true
            height: 64
            radius: 14
            color: "#0E1624"
            border.width: 1
            border.color: "#1C2A3C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: "ACCÉLÉRATEUR"
                        color: "#BAC8D9"
                        font.family: T.StyleManager.fontFamily
                        font.pixelSize: 11
                        font.weight: Font.Bold
                        font.letterSpacing: 1
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: Math.round(S.UiState.throttle) + " %"
                        color: "#FFFFFF"
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
                        width: parent.width * Math.min(1.0, Math.max(0.0, S.UiState.throttle / 100.0))
                        height: parent.height
                        radius: 2.5
                        color: S.UiState.throttle > 85 ? T.StyleManager.warning : T.StyleManager.accent
                        Behavior on width { NumberAnimation { duration: 100 } }
                    }
                }
            }
        }

        // Odomètre Totalisateur
        Rectangle {
            Layout.preferredWidth: 175
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
                    text: "TOTALISATEUR"
                    color: "#BAC8D9"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.fixed(S.UiState.odometer, 0, "0") + " km"
                    color: "#FFFFFF"
                    font.family: T.StyleManager.fontFamily
                    font.pixelSize: 17
                    font.weight: Font.Bold
                }
            }
        }
    }
}
