import QtQuick
import "../../../style" as T

// Métrique haute visibilité — label + valeur + unité
Column {
    id: root
    property string label:      "MÉTRIQUE"
    property string value:      "—"
    property string unit:       ""
    property color  valueColor: "#FFFFFF"
    property int    valueSize:  32
    property int    alignment:  Text.AlignLeft
    property bool   animated:   true

    spacing: 3

    Text {
        text: root.label.toUpperCase()
        color: Qt.rgba(1.0, 1.0, 1.0, 0.45)
        font.pixelSize: 11
        font.weight: Font.Bold
        font.letterSpacing: 1.2
        horizontalAlignment: root.alignment
    }

    Row {
        anchors.right: root.alignment === Text.AlignRight ? parent.right : undefined
        anchors.horizontalCenter: root.alignment === Text.AlignHCenter ? parent.horizontalCenter : undefined
        spacing: 4

        Text {
            text: root.value
            color: root.valueColor
            font.pixelSize: root.valueSize
            font.weight: Font.Black
            font.letterSpacing: -0.5

            Behavior on color { ColorAnimation { duration: 250 } }
        }

        Text {
            visible: root.unit !== ""
            text: root.unit
            color: Qt.rgba(
                root.valueColor.r,
                root.valueColor.g,
                root.valueColor.b,
                0.60
            )
            font.pixelSize: Math.max(12, root.valueSize * 0.45)
            font.weight: Font.Bold
            anchors.baseline: parent.children[0] ? parent.children[0].baseline : undefined
        }
    }
}
