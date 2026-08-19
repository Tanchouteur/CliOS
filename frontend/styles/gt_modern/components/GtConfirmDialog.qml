import QtQuick
import "../../../style" as T

Rectangle {
    id: root
    signal accepted()
    signal rejected()
    property string title: "Confirmer l’action"
    property string message: "Cette action nécessite votre confirmation."
    property string acceptText: "CONFIRMER"
    property bool dangerous: true
    visible: false
    anchors.fill: parent
    color: Qt.rgba(0.02, 0.03, 0.04, 0.96)

    Rectangle {
        width: 760
        height: 340
        anchors.centerIn: parent
        color: T.StyleManager.surface
        radius: T.StyleManager.radiusLarge
        border.width: 2
        border.color: root.dangerous ? T.StyleManager.danger : T.StyleManager.accent

        Column {
            anchors.fill: parent
            anchors.margins: 38
            spacing: 24
            Text {
                width: parent.width
                text: root.title
                color: T.StyleManager.text
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 34
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                width: parent.width
                height: 80
                text: root.message
                color: T.StyleManager.textSecondary
                font.family: T.StyleManager.fontFamily
                font.pixelSize: 21
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 20
                GtButton { text: "ANNULER"; width: 250; onClicked: root.rejected() }
                GtButton {
                    text: root.acceptText
                    width: 300
                    primary: !root.dangerous
                    destructive: root.dangerous
                    onClicked: root.accepted()
                }
            }
        }
    }
}
