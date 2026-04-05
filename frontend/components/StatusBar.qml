import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Rectangle {
    id: statusBar
    height: 35
    width: parent.width*0.2
    color: Qt.rgba(0, 0, 0, 0.5)
    z: 100

    property var health: bridge.systemHealth !== undefined ? bridge.systemHealth : {}

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 15

        Item { Layout.fillWidth: true }

        // --- DROITE : État des Services ---
        Row {
            spacing: 12
            Layout.alignment: Qt.AlignVCenter

            Repeater {
                model: Object.keys(statusBar.health)

                delegate: Row {
                    spacing: 6
                    property var service: statusBar.health[modelData]


                    Rectangle {
                        width: 8; height: 8; radius: 4
                        anchors.verticalCenter: parent.verticalCenter
                        color: {
                            if (service.status === "OK") return "#00ff00"
                            if (service.status === "WARNING") return "#ffaa00"
                            return "#ff0000"
                        }

                        // Animation de pulsation si erreur
                        SequentialAnimation on opacity {
                            running: service.status !== "OK"
                            loops: Animation.Infinite
                            NumberAnimation { to: 0.3; duration: 500 }
                            NumberAnimation { to: 1.0; duration: 500 }
                        }
                    }

                    // Nom du service
                    Text {
                        text: modelData
                        color: service.status === "OK" ? T.Theme.textDimmed : "white"
                        font.pixelSize: 10
                        font.bold: service.status !== "OK"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }
}