import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../style" as T

Rectangle {
    id: statusBar
    height: 35
    width: parent.width * 0.2
    color: T.Theme.bgMain
    z: 100

    // --- DONNÉES ---
    property var health: bridge && bridge.systemHealth !== undefined ? bridge.systemHealth : {}

    // Séparation des services sains et des services en erreur
    property var allKeys: Object.keys(statusBar.health)
    property var problemKeys: allKeys.filter(k => statusBar.health[k].status !== "OK")
    property var okKeys: allKeys.filter(k => statusBar.health[k].status === "OK")

    // État du menu déroulant
    property bool isDropdownOpen: false

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 20
        anchors.rightMargin: 20
        spacing: 15

        Item { Layout.fillWidth: false} // Pousse tout vers la droite

        // --- ZONE DE DROITE ---
        Row {
            spacing: 15
            Layout.alignment: Qt.AlignVCenter

            // 1. Les services EN ERREUR (Toujours visibles)
            Row {
                spacing: 12
                Repeater {
                    model: statusBar.problemKeys
                    delegate: Row {
                        spacing: 6
                        property var service: statusBar.health[modelData]

                        Rectangle {
                            width: 10; height: 10; radius: 5
                            anchors.verticalCenter: parent.verticalCenter
                            color: service.status === "WARNING" ? "#ffaa00" : "#ff0000"

                            SequentialAnimation on opacity {
                                running: true
                                loops: Animation.Infinite
                                NumberAnimation { to: 0.3; duration: 500 }
                                NumberAnimation { to: 1.0; duration: 500 }
                            }
                        }

                        Text {
                            text: modelData
                            color: "white"
                            font.pixelSize: 11
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            // 2. Le bouton des services OK (Cliquable)
            Rectangle {
                width: okKeys.length > 0 ? okText.width + 20 : 0
                height: 24
                radius: 12
                color: Qt.rgba(0, 1, 0, 0.1) // Fond vert très léger
                border.color: "#00ff00"
                border.width: 1
                visible: okKeys.length > 0
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    id: okText
                    text: "✓ " + statusBar.okKeys.length + " OK"
                    color: "#00ff00"
                    font.pixelSize: 11
                    font.bold: true
                    anchors.centerIn: parent
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: statusBar.isDropdownOpen = !statusBar.isDropdownOpen
                }
            }
        }
    }

    // --- LE MENU DÉROULANT (Flottant sous la barre) ---
    Rectangle {
        id: dropdownMenu
        visible: statusBar.isDropdownOpen

        // Positionnement juste sous la barre, aligné à droite
        anchors.top: statusBar.bottom
        anchors.topMargin: 5
        anchors.right: parent.right
        anchors.rightMargin: 20

        // Taille dynamique en fonction du nombre de services
        width: 150
        height: okColumn.height + 20
        radius: 8
        color: Qt.rgba(0.1, 0.1, 0.1, 0.95)
        border.color: Qt.rgba(1, 1, 1, 0.2)

        Column {
            id: okColumn
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 10
            spacing: 8

            Repeater {
                model: statusBar.okKeys
                delegate: Row {
                    spacing: 8

                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: "#00ff00"
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        text: modelData
                        color: T.Theme.textMain || "white" // Utilise ton thème
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }
}