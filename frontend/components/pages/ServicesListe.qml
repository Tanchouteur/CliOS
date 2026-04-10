import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../../style" as T

Item {
    id: systemPage

    // 1. LA LISTE DYNAMIQUE (Extraite directement du Python)
    property var serviceKeys: (bridge !== undefined && bridge.systemHealth !== undefined) ? Object.keys(bridge.systemHealth) : []

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // --- EN-TÊTE (Bouton Retour + Titre) ---
        RowLayout {
            Layout.fillWidth: true
            spacing: 15

            Rectangle {
                width: 40; height: 40; radius: 20
                color: backMouse.containsMouse ? T.Theme.main : T.Theme.bgDimmed
                border.color: Qt.rgba(1, 1, 1, 0.1)
                border.width: 1

                Text {
                    text: "〈"
                    color: T.Theme.textMain
                    font.pixelSize: 20
                    font.bold: true
                    anchors.centerIn: parent
                    transform: Translate { x: -2 }
                }

                MouseArea {
                    id: backMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: systemPage.StackView.view.pop()
                }
            }

            Text {
                text: "GESTIONNAIRE DE SERVICES"
                color: T.Theme.textMain
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
            }
        }

        // --- LISTE GÉNÉRÉE AUTOMATIQUEMENT ---
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: systemPage.serviceKeys
            spacing: 12
            clip: true

            delegate: Rectangle {
                id: serviceCard
                width: ListView.view.width
                height: 80
                color: T.Theme.bgDimmed
                radius: 12
                border.color: cardMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.2) : Qt.rgba(1, 1, 1, 0.05)

                scale: cardMouse.pressed ? 0.98 : 1.0
                Behavior on scale { NumberAnimation { duration: 100 } }

                // Variables simplifiées pour lire les données du service actuel
                property string serviceId: modelData
                property var srv: bridge.systemHealth[serviceId]
                property bool isOn: srv !== undefined && srv.status !== "DISABLED"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    spacing: 15

                    // Textes
                    Column {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 4

                        Text {
                            text: serviceCard.serviceId // Le vrai nom du service
                            color: serviceCard.isOn ? T.Theme.textMain : T.Theme.unselected
                            font.pixelSize: 18
                            font.bold: true
                        }
                        Text {
                            // On affiche ce que le service a à nous dire !
                            text: serviceCard.srv !== undefined ? serviceCard.srv.message : "En attente..."
                            color: serviceCard.isOn ? T.Theme.textDimmed : T.Theme.unselected
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            width: parent.width
                        }
                    }

                    // --- INTERRUPTEUR ---
                    Rectangle {
                        id: toggleTrack
                        width: 50; height: 28; radius: 14
                        color: serviceCard.isOn ? T.Theme.main : "#222222"
                        border.color: serviceCard.isOn ? T.Theme.main : "#444444"
                        Layout.alignment: Qt.AlignVCenter

                        Behavior on color { ColorAnimation { duration: 200 } }

                        Rectangle {
                            id: toggleKnob
                            width: 24; height: 24; radius: 12
                            color: "#ffffff"
                            y: 2
                            x: serviceCard.isOn ? (toggleTrack.width - width - 2) : 2

                            Behavior on x { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
                            layer.enabled: true
                        }
                    }
                }

                // Action de clic
                MouseArea {
                    id: cardMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: {
                        bridge.toggleService(serviceCard.serviceId, !serviceCard.isOn);
                    }
                }
            }
        }
    }
}