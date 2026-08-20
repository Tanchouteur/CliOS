import QtQuick
import QtQuick.Layouts
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    signal settingsRequested(string route)
    signal commandRequested(string command)

    Rectangle {
        anchors.fill: parent
        color: "#D9000000"
        radius: 24
        border.width: 2
        border.color: T.StyleManager.accent
    }

    ColumnLayout {
        anchors.centerIn: parent
        width: 720
        spacing: 18
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Math.round(S.UiState.speed)
            color: "white"; font.pixelSize: 120; font.bold: true
        }
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "km/h · " + Math.round(S.UiState.rpm) + " tr/min"
            color: T.StyleManager.textSecondary; font.pixelSize: 24
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 12
            Repeater {
                model: [
                    {label: "APPARENCE", route: "appearance"},
                    {label: "VÉHICULE", route: "vehicle"},
                    {label: "SERVICES", route: "services"},
                    {label: "SYSTÈME", route: "system"},
                    {label: "DIAGNOSTIC", route: "diagnostic"}
                ]
                Rectangle {
                    Layout.fillWidth: true; height: 58; radius: 10
                    color: "#252525"; border.width: 1; border.color: T.StyleManager.outline
                    Text { anchors.centerIn: parent; text: modelData.label; color: "white"; font.pixelSize: 13; font.bold: true }
                    MouseArea { anchors.fill: parent; onClicked: root.settingsRequested(modelData.route) }
                }
            }
        }
    }
}
