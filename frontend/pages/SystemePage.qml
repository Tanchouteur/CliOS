import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../style" as T
import "../components" as C

Item {
    id: root

    // Modèle des sous-options du menu Système
    readonly property var menuItems: [
        { label: "Services", desc: "Activer ou désactiver les modules (Audio, Leds, etc.)", source: "ServicesPage.qml" },
        { label: "Informations", desc: "Version du logiciel, état CPU et RAM", source: "NonBuildPage.qml" },
        { label: "Journal", desc: "Consulter les logs d'erreurs du système", source: "NonBuildPage.qml" }
    ]

    // --- HEADER ---
    C.PageHeader {
        id: header
        title: "SYSTÈME"

        onBackClicked: {
            root.StackView.view.pop()
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20
        anchors.topMargin: header.height + 50


        // --- LISTE DES OPTIONS (Même D.A. que Settings) ---
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.menuItems
            spacing: 12
            clip: true

            delegate: Rectangle {
                id: menuTile
                width: ListView.view.width
                height: 90
                color: T.Theme.bgDimmed
                radius: 12
                border.color: tileMouse.containsMouse ? T.Theme.main : Qt.rgba(1, 1, 1, 0.05)
                border.width: tileMouse.containsMouse ? 2 : 1

                scale: tileMouse.pressed ? 0.98 : 1.0
                Behavior on scale { NumberAnimation { duration: 100 } }
                Behavior on border.color { ColorAnimation { duration: 200 } }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 25
                    anchors.rightMargin: 25
                    spacing: 20

                    Column {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 4
                        Text {
                            text: modelData.label
                            color: T.Theme.textMain
                            font.pixelSize: 20; font.bold: true
                        }
                        Text {
                            text: modelData.desc
                            color: T.Theme.unselected
                            font.pixelSize: 13
                        }
                    }

                    Text {
                        text: "〉"
                        color: tileMouse.containsMouse ? T.Theme.main : T.Theme.unselected
                        font.pixelSize: 20; font.bold: true
                        transform: Translate { x: tileMouse.containsMouse ? 5 : 0 }
                        Behavior on transform { NumberAnimation { duration: 200 } }
                    }
                }

                MouseArea {
                    id: tileMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.StackView.view.push(Qt.resolvedUrl(modelData.source))
                }
            }
        }
    }
}