import QtQuick
import "../../../style" as T

Item {
    id: root
    height: 68
    property string current: "drive"
    signal tabSelected(string tabId)

    readonly property var tabs: [
        { id: "drive", number: "01", label: "CONDUITE" },
        { id: "perf", number: "02", label: "PERFORMANCE" },
        { id: "menu", number: "03", label: "COMMANDES" }
    ]

    Rectangle {
        anchors.fill: parent
        color: "#FA05090E"
        Rectangle { width: parent.width; height: 1; color: "#344A60" }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(1050, parent.width - 80)
        height: 56
        radius: 20
        color: "#0B1119"
        border.width: 1
        border.color: "#293E52"

        Row {
            anchors.fill: parent
            anchors.margins: 4

            Repeater {
                model: root.tabs
                delegate: Item {
                    width: parent.width / 3
                    height: parent.height
                    readonly property bool active: root.current === modelData.id

                    Rectangle {
                        anchors.fill: parent
                        radius: 16
                        color: active ? "#173144" : (touch.pressed ? "#121E29" : "transparent")
                        border.width: active ? 1 : 0
                        border.color: active ? T.StyleManager.accent : "transparent"

                        Rectangle {
                            visible: active
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: parent.width * 0.48
                            height: 3
                            radius: 2
                            color: T.StyleManager.accent
                        }
                    }

                    Row {
                        anchors.centerIn: parent
                        spacing: 13
                        scale: touch.pressed ? 0.97 : 1.0
                        Behavior on scale { NumberAnimation { duration: 90 } }

                        Text {
                            text: modelData.number
                            color: active ? T.StyleManager.accent : "#7F91A2"
                            font.pixelSize: 12
                            font.weight: Font.Black
                            font.letterSpacing: 1.0
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.label
                            color: active ? "#FFFFFF" : "#AAB8C4"
                            font.pixelSize: 15
                            font.weight: Font.Bold
                            font.letterSpacing: 2.0
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: touch
                        anchors.fill: parent
                        onClicked: root.tabSelected(modelData.id)
                    }
                }
            }
        }
    }
}
