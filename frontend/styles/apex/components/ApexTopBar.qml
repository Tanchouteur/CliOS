import QtQuick
import "../../../state" as S
import "../../../style" as T

// Barre d'état minimaliste : heure + temp + voyants + USB
Rectangle {
    id: root
    width: parent.width
    height: 46
    color: Qt.rgba(0.03, 0.07, 0.13, 0.88)

    // Heure
    property string timeText: Qt.formatTime(new Date(), "HH:mm")
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.timeText = Qt.formatTime(new Date(), "HH:mm") }

    Row {
        id: leftRow
        anchors.left: parent.left
        anchors.leftMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 16

        // Heure
        Text {
            text: root.timeText
            color: "#FFFFFF"
            font.pixelSize: 22
            font.weight: Font.Bold
            font.letterSpacing: 1.0
        }

        // Séparateur
        Rectangle { width: 1; height: 22; color: Qt.rgba(1,1,1,0.12); anchors.verticalCenter: parent.verticalCenter }

        // Température extérieure
        Text {
            text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—") + " °C"
            color: "#C8D4E0"
            font.pixelSize: 17
            font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }

        // Séparateur
        Rectangle { width: 1; height: 22; color: Qt.rgba(1,1,1,0.12); anchors.verticalCenter: parent.verticalCenter }

        // Nom du véhicule
        Text {
            text: S.UiState.vehicleName !== undefined ? S.UiState.vehicleName : (S.UiState.profileName ? S.UiState.profileName() : "CliOS")
            color: T.StyleManager.accent
            font.pixelSize: 17
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // Voyants centraux
    Row {
        anchors.centerIn: parent
        spacing: 6

        Repeater {
            model: S.UiState.indicators
            delegate: Rectangle {
                visible: modelData.active
                width:  lcode.implicitWidth + 18
                height: 26
                radius: 5
                color: Qt.rgba(
                    Qt.color(modelData.color).r,
                    Qt.color(modelData.color).g,
                    Qt.color(modelData.color).b,
                    0.18
                )
                border.width: 1
                border.color: Qt.color(modelData.color)

                SequentialAnimation on opacity {
                    running: modelData.active && modelData.blink
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.2; duration: 380 }
                    NumberAnimation { to: 1.0; duration: 380 }
                }

                Text {
                    id: lcode
                    anchors.centerIn: parent
                    text: modelData.code
                    color: Qt.color(modelData.color)
                    font.pixelSize: 11
                    font.weight: Font.Bold
                }
            }
        }
    }

    // Droite : USB + erreurs services
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        // Erreurs services
        Rectangle {
            visible: (S.UiState.serviceErrorKeys.length + S.UiState.serviceWarningKeys.length) > 0
            width: errText.implicitWidth + 18
            height: 26
            radius: 5
            color: Qt.rgba(1.0, 0.27, 0.27, 0.15)
            border.width: 1
            border.color: S.UiState.serviceErrorKeys.length > 0 ? "#FF4444" : "#FFB300"
            Text {
                id: errText
                anchors.centerIn: parent
                text: S.UiState.serviceErrorKeys.length + " ERR · " + S.UiState.serviceWarningKeys.length + " AVIS"
                color: S.UiState.serviceErrorKeys.length > 0 ? "#FF4444" : "#FFB300"
                font.pixelSize: 11
                font.weight: Font.Bold
            }
        }

        // Badge USB
        Rectangle {
            width: usbText.implicitWidth + 18
            height: 26
            radius: 5
            color: S.UiState.ramMode
                ? Qt.rgba(1.0, 0.27, 0.27, 0.12)
                : Qt.rgba(0.0, 0.85, 0.5, 0.10)
            border.width: 1
            border.color: S.UiState.ramMode ? "#FF4444" : "#00E676"
            Text {
                id: usbText
                anchors.centerIn: parent
                text: S.UiState.ramMode
                    ? "RAM"
                    : (S.UiState.storage && S.UiState.storage.free_space_mb !== undefined
                       ? Math.round(S.UiState.storage.free_space_mb) + " MB"
                       : "USB")
                color: S.UiState.ramMode ? "#FF4444" : "#00E676"
                font.pixelSize: 11
                font.weight: Font.Bold
            }
        }

        // Version
        Text {
            text: "APEX"
            color: Qt.rgba(1, 1, 1, 0.25)
            font.pixelSize: 11
            font.weight: Font.Bold
            font.letterSpacing: 2.0
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // Ligne de séparation bottom
    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Qt.rgba(1, 1, 1, 0.06)
    }
}
