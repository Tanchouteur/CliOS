import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../components"

Item {
    id: root
    anchors.fill: parent

    signal navigateRequested(string target)
    signal actionRequested(string action)

    readonly property var sections: [
        { id: "appearance", number: "01", label: "APPARENCE", sub: "Ambiance, couleurs et style du cockpit", tone: "accent" },
        { id: "vehicle", number: "02", label: "VÉHICULE", sub: "Profil actif, capteurs et étalonnage", tone: "normal" },
        { id: "services", number: "03", label: "SERVICES", sub: "Modules et fonctions embarquées", tone: "normal" },
        { id: "system", number: "04", label: "SYSTÈME", sub: "Santé, stockage et journaux", tone: "normal" },
        { id: "developer", number: "05", label: "DÉVELOPPEUR", sub: "CAN, diagnostic et outils avancés", tone: "normal" },
        { id: "_power", number: "06", label: "ALIMENTATION", sub: "Redémarrer, quitter ou éteindre", tone: "danger" }
    ]

    GridLayout {
        anchors.fill: parent
        anchors.margins: 14
        columns: 3
        rowSpacing: 14
        columnSpacing: 14

        Repeater {
            model: root.sections
            delegate: ApexCard3D {
                id: menuCard
                Layout.fillWidth: true
                Layout.fillHeight: true
                highlighted: modelData.tone === "accent"
                glowColor: modelData.tone === "danger" ? "#FF6670" : T.StyleManager.accent

                Rectangle {
                    anchors.fill: parent
                    radius: 18
                    color: cardTouch.pressed
                        ? (modelData.tone === "danger" ? "#25131A" : "#132B3A")
                        : "transparent"
                }

                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Text {
                        text: modelData.number
                        color: modelData.tone === "danger" ? "#FF7780" : T.StyleManager.accent
                        font.pixelSize: 13
                        font.weight: Font.Black
                        font.letterSpacing: 2.0
                    }
                    Text {
                        text: modelData.label
                        color: "#FFFFFF"
                        font.pixelSize: 23
                        font.weight: Font.Black
                        font.letterSpacing: 2.2
                    }
                    Text {
                        text: modelData.sub
                        color: "#B1BFCC"
                        font.pixelSize: 14
                        font.weight: Font.Medium
                    }
                }

                Rectangle {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: 52
                    height: 52
                    radius: 18
                    color: modelData.tone === "danger" ? "#28141B" : "#102231"
                    border.width: 1
                    border.color: modelData.tone === "danger" ? "#8B3A45" : "#36546C"

                    Text {
                        anchors.centerIn: parent
                        text: "›"
                        color: modelData.tone === "danger" ? "#FF7780" : "#FFFFFF"
                        font.pixelSize: 32
                        font.weight: Font.Light
                    }
                }

                MouseArea {
                    id: cardTouch
                    anchors.fill: parent
                    onClicked: {
                        if (modelData.id === "_power") powerMenu.visible = true
                        else root.navigateRequested(modelData.id)
                    }
                }
            }
        }
    }

    Rectangle {
        id: powerMenu
        anchors.fill: parent
        visible: false
        color: "#E603060A"
        z: 100

        MouseArea { anchors.fill: parent; onClicked: powerMenu.visible = false }

        Rectangle {
            anchors.centerIn: parent
            width: 720
            height: 344
            radius: 30
            color: "#0B121B"
            border.width: 1
            border.color: "#41576C"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 26
                spacing: 14

                RowLayout {
                    Layout.fillWidth: true
                    Column {
                        Layout.fillWidth: true
                        spacing: 4
                        Text { text: "ALIMENTATION"; color: "#FFFFFF"; font.pixelSize: 22; font.bold: true; font.letterSpacing: 2.4 }
                        Text { text: "Choisissez une action système"; color: "#B2C0CC"; font.pixelSize: 14 }
                    }
                    Rectangle {
                        width: 52; height: 52; radius: 18; color: closeTouch.pressed ? "#22303D" : "#141E28"; border.width: 1; border.color: "#3C5063"
                        Text { anchors.centerIn: parent; text: "×"; color: "#FFFFFF"; font.pixelSize: 28 }
                        MouseArea { id: closeTouch; anchors.fill: parent; onClicked: powerMenu.visible = false }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: "#31465A" }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 12
                    Repeater {
                        model: [
                            { label: "QUITTER CLIOS", action: "quit", danger: false },
                            { label: "REDÉMARRER", action: "restart", danger: false },
                            { label: "ÉTEINDRE", action: "shutdown", danger: true }
                        ]
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 20
                            color: actionTouch.pressed ? (modelData.danger ? "#4A1C24" : "#173246") : (modelData.danger ? "#28141B" : "#101D29")
                            border.width: 1
                            border.color: modelData.danger ? "#B34854" : "#36536B"
                            Column {
                                anchors.centerIn: parent
                                spacing: 12
                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.danger ? "!" : "•"; color: modelData.danger ? "#FF7780" : T.StyleManager.accent; font.pixelSize: 32; font.bold: true }
                                Text { text: modelData.label; color: "#FFFFFF"; font.pixelSize: 14; font.bold: true; font.letterSpacing: 1.4 }
                            }
                            MouseArea {
                                id: actionTouch
                                anchors.fill: parent
                                onClicked: {
                                    powerMenu.visible = false
                                    root.actionRequested(modelData.action)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
