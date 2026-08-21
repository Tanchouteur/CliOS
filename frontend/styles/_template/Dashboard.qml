import QtQuick
import "../../state" as S

Item {
    signal settingsRequested(string route)
    signal commandRequested(string command)
    anchors.fill: parent

    Text {
        anchors.centerIn: parent
        text: Math.round(S.UiState.speed) + " km/h"
        color: "white"
        font.pixelSize: 72
    }

    MouseArea { anchors.fill: parent; onClicked: parent.settingsRequested("appearance") }
}
