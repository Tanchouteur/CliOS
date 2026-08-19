import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T

Item {
    id: root
    height: 54
    property string timeText: Qt.formatTime(new Date(), "HH:mm")

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.timeText = Qt.formatTime(new Date(), "HH:mm")
    }

    Rectangle {
        anchors.fill: parent
        color: "#F20A111A"
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#30445A" }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 22
        anchors.rightMargin: 22
        spacing: 16

        Text {
            text: root.timeText
            color: "#FFFFFF"
            font.pixelSize: 25
            font.weight: Font.Black
            font.letterSpacing: 0.8
        }

        Rectangle { width: 1; height: 26; color: "#3B5065" }

        Text {
            text: S.UiState.fixed(S.UiState.outsideTemp, 1, "—") + " °C"
            color: "#D2DEE8"
            font.pixelSize: 17
            font.weight: Font.Bold
        }

        Text {
            text: "APEX"
            color: T.StyleManager.accent
            font.pixelSize: 15
            font.weight: Font.Black
            font.letterSpacing: 3.6
            Layout.leftMargin: 12
        }

        Item { Layout.fillWidth: true }

        // Les alertes actives restent au centre du champ visuel.
        Row {
            spacing: 8
            Layout.alignment: Qt.AlignVCenter
            Repeater {
                model: S.UiState.indicators
                delegate: Rectangle {
                    visible: modelData.active
                    width: warningText.implicitWidth + 22
                    height: 32
                    radius: 16
                    color: Qt.rgba(Qt.color(modelData.color).r, Qt.color(modelData.color).g, Qt.color(modelData.color).b, 0.16)
                    border.width: 1
                    border.color: modelData.color
                    Text {
                        id: warningText
                        anchors.centerIn: parent
                        text: modelData.code
                        color: modelData.color
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 1.0
                    }
                    SequentialAnimation on opacity {
                        running: modelData.active && modelData.blink
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.35; duration: 360 }
                        NumberAnimation { to: 1.0; duration: 360 }
                    }
                }
            }
        }

        Item { Layout.fillWidth: true }

        Rectangle {
            visible: S.UiState.serviceErrorKeys.length + S.UiState.serviceWarningKeys.length > 0
            width: serviceText.implicitWidth + 24
            height: 32
            radius: 16
            color: "#351820"
            border.width: 1
            border.color: S.UiState.serviceErrorKeys.length > 0 ? "#FF6670" : "#FFB84D"
            Text {
                id: serviceText
                anchors.centerIn: parent
                text: S.UiState.serviceErrorKeys.length > 0 ? "SERVICE À CONTRÔLER" : "AVIS SYSTÈME"
                color: S.UiState.serviceErrorKeys.length > 0 ? "#FF7B84" : "#FFD17D"
                font.pixelSize: 12
                font.bold: true
                font.letterSpacing: 1.1
            }
        }

        Row {
            spacing: 9
            Rectangle {
                width: 10; height: 10; radius: 5
                color: S.UiState.ramMode ? "#FF6670" : "#54E3A5"
                anchors.verticalCenter: parent.verticalCenter
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 0
                Text {
                    text: S.UiState.ramMode ? "MÉMOIRE INTERNE" : "STOCKAGE CONNECTÉ"
                    color: "#E5EDF4"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 1.2
                }
                Text {
                    text: S.UiState.ramMode ? "MODE DÉGRADÉ" : Math.round(S.UiState.storageFreeMb) + " MB LIBRES"
                    color: "#91A4B5"
                    font.pixelSize: 10
                    font.bold: true
                }
            }
        }
    }
}
