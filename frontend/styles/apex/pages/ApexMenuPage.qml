import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T
import "../components"

// Page menu simplifié — grille 3×2 de cartes 3D animées
Item {
    id: root
    anchors.fill: parent

    signal navigateRequested(string target)
    signal actionRequested(string action)

    readonly property var sections: [
        { id: "appearance", icon: "◈", label: "APPARENCE",   sub: "Thèmes & accents" },
        { id: "vehicle",    icon: "◎", label: "VÉHICULE",    sub: "Profil & capteurs" },
        { id: "services",   icon: "◉", label: "SERVICES",    sub: "Modules backend" },
        { id: "system",     icon: "◇", label: "SYSTÈME",     sub: "Logs & stockage" },
        { id: "developer",  icon: "◈", label: "DÉVELOPPEUR", sub: "CAN & debug" },
        { id: "_power",     icon: "◎", label: "ALIMENTATION", sub: "Quitter / Éteindre" }
    ]

    GridLayout {
        anchors.fill: parent
        anchors.margins: 12
        columns: 3
        rowSpacing: 10
        columnSpacing: 10

        Repeater {
            model: root.sections
            delegate: ApexCard3D {
                Layout.fillWidth: true
                Layout.fillHeight: true
                id: cardItem
                property int entryDelay: (index || 0) * 60
                Component.onCompleted: {
                    opacity = 0
                    entryTimer.start()
                }
                Timer {
                    id: entryTimer
                    interval: Math.max(1, cardItem.entryDelay)
                    onTriggered: {
                        cardItem.opacity = 0
                        entryAnim.start()
                    }
                }
                NumberAnimation {
                    id: entryAnim
                    target: cardItem
                    property: "opacity"
                    from: 0; to: 1
                    duration: 380
                    easing.type: Easing.OutCubic
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 8

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData.icon
                        color: modelData.id === "_power"
                            ? "#FF4444"
                            : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.7)
                        font.pixelSize: 28
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData.label
                        color: "#FFFFFF"
                        font.pixelSize: 17
                        font.weight: Font.Black
                        font.letterSpacing: 2.5
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: modelData.sub
                        color: Qt.rgba(1, 1, 1, 0.35)
                        font.pixelSize: 13
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onPressed:  parent.opacity = 0.75
                    onReleased: parent.opacity = 1.0
                    onClicked: {
                        if (modelData.id === "_power") {
                            powerMenu.visible = true
                        } else {
                            root.navigateRequested(modelData.id)
                        }
                    }
                }
            }
        }
    }

    // Sous-menu alimentation flottant
    Rectangle {
        id: powerMenu
        visible: false
        anchors.fill: parent
        color: Qt.rgba(0.02, 0.04, 0.08, 0.92)

        Rectangle {
            anchors.centerIn: parent
            width: 480; height: 280
            radius: T.StyleManager.radiusLarge
            color: "#0E1828"
            border.width: 1
            border.color: Qt.rgba(1, 0.2, 0.2, 0.4)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 28
                spacing: 14

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "ALIMENTATION"
                    color: "#FFFFFF"
                    font.pixelSize: 18
                    font.weight: Font.Black
                    font.letterSpacing: 3
                }

                Item { Layout.fillHeight: true }

                Repeater {
                    model: [
                        { label: "QUITTER CLIOS",  action: "quit",     danger: false },
                        { label: "REDÉMARRER",      action: "restart",  danger: true  },
                        { label: "ÉTEINDRE",        action: "shutdown", danger: true  }
                    ]
                    Rectangle {
                        Layout.fillWidth: true
                        height: 48
                        radius: T.StyleManager.radiusSmall
                        color: modelData.danger
                            ? Qt.rgba(1.0, 0.2, 0.1, 0.10)
                            : Qt.rgba(0.1, 0.3, 0.6, 0.10)
                        border.width: 1
                        border.color: modelData.danger
                            ? Qt.rgba(1.0, 0.2, 0.1, 0.4)
                            : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.35)

                        Text {
                            anchors.centerIn: parent
                            text: modelData.label
                            color: modelData.danger ? "#FF4444" : T.StyleManager.accent
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            font.letterSpacing: 2
                        }
                        MouseArea {
                            anchors.fill: parent
                            onPressed: parent.opacity = 0.7
                            onReleased: parent.opacity = 1.0
                            onClicked: {
                                powerMenu.visible = false
                                root.actionRequested(modelData.action)
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    radius: T.StyleManager.radiusSmall
                    color: Qt.rgba(1, 1, 1, 0.06)
                    border.width: 1
                    border.color: Qt.rgba(1, 1, 1, 0.12)
                    Text {
                        anchors.centerIn: parent
                        text: "ANNULER"
                        color: Qt.rgba(1, 1, 1, 0.45)
                        font.pixelSize: 14
                        font.weight: Font.Bold
                        font.letterSpacing: 2
                    }
                    MouseArea { anchors.fill: parent; onClicked: powerMenu.visible = false }
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            z: -1
            onClicked: powerMenu.visible = false
        }
    }
}
