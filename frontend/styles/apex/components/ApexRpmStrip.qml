import QtQuick
import "../../../state" as S
import "../../../style" as T

Item {
    id: root
    implicitHeight: 20

    readonly property real ratio: Math.max(0, Math.min(1, S.UiState.rpm / Math.max(1, S.UiState.maxRpm)))
    readonly property bool redline: S.UiState.redline
    property real animatedRatio: ratio
    property real flash: 1.0

    Behavior on animatedRatio { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
    SequentialAnimation on flash {
        running: root.redline
        loops: Animation.Infinite
        NumberAnimation { to: 0.35; duration: 120 }
        NumberAnimation { to: 1.0; duration: 120 }
    }
    onRedlineChanged: if (!redline) flash = 1.0

    // Rail inférieur embossé.
    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: "#081019"
        border.width: 1
        border.color: "#24384A"
    }

    Row {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 4

        Repeater {
            model: 32
            Rectangle {
                readonly property real p: index / 31
                readonly property bool active: p <= root.animatedRatio
                width: Math.max(2, (parent.width - 31 * parent.spacing) / 32)
                height: parent.height
                radius: 3
                opacity: root.redline && p > 0.82 ? root.flash : 1.0
                color: {
                    if (!active) return p > 0.82 ? "#332127" : "#17232E"
                    if (p > 0.88) return "#FF4E5B"
                    if (p > 0.72) return "#FFB84D"
                    return T.StyleManager.accent
                }
                Behavior on color { ColorAnimation { duration: 90 } }
            }
        }
    }
}
