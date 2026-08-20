import QtQuick
import QtQuick.Layouts
import "../../../style" as T

Item {
    id: root
    anchors.fill: parent
    visible: opacity > 0.01
    opacity: 0.0
    Behavior on opacity { NumberAnimation { duration: 180 } }

    property string title: ""
    property string message: ""
    property string acceptText: "CONFIRMER"
    property bool dangerous: false

    signal accepted()
    signal rejected()

    function open() { opacity = 1.0 }
    function close() { opacity = 0.0 }

    Rectangle {
        anchors.fill: parent
        color: "#E604060A"
        MouseArea { anchors.fill: parent; onClicked: root.rejected() }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 580
        height: 280
        radius: 18
        color: "#0E1522"
        border.width: 2
        border.color: root.dangerous ? T.StyleManager.danger : T.StyleManager.accent

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: root.title
                color: "#FFFFFF"
                font.family: "Arial, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                font.letterSpacing: 1.2
            }

            Text {
                Layout.fillWidth: true
                text: root.message
                color: "#BAC8D9"
                font.family: "Arial, sans-serif"
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }

            Item { Layout.fillHeight: true }

            RowLayout {
                Layout.fillWidth: true
                spacing: 16

                Rectangle {
                    Layout.fillWidth: true; height: 48; radius: 10
                    color: "#182436"
                    border.width: 1; border.color: Qt.rgba(1, 1, 1, 0.15)
                    Text { anchors.centerIn: parent; text: "ANNULER"; color: "#BAC8D9"; font.pixelSize: 13; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.rejected() }
                }

                Rectangle {
                    Layout.fillWidth: true; height: 48; radius: 10
                    color: root.dangerous ? T.StyleManager.danger : T.StyleManager.accent
                    Text { anchors.centerIn: parent; text: root.acceptText; color: "#000000"; font.pixelSize: 13; font.bold: true }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.accepted() }
                }
            }
        }
    }
}
