import QtQuick
import "../style" as T

Column {
    id: root
    property string label: "MÉTRIQUE"
    property string value: "—"
    property string unit: ""
    property color valueColor: T.StyleManager.text
    property int valueSize: 32
    property int alignment: Text.AlignLeft
    spacing: 4

    Text {
        width: parent.width
        text: root.label.toUpperCase()
        color: T.StyleManager.textSecondary
        font.family: T.StyleManager.fontFamily
        font.pixelSize: 16
        font.weight: Font.Medium
        horizontalAlignment: root.alignment
        elide: Text.ElideRight
    }

    Row {
        anchors.right: root.alignment === Text.AlignRight ? parent.right : undefined
        anchors.horizontalCenter: root.alignment === Text.AlignHCenter ? parent.horizontalCenter : undefined
        spacing: 6

        Text {
            text: root.value
            color: root.valueColor
            font.family: T.StyleManager.fontFamily
            font.pixelSize: root.valueSize
            font.weight: Font.DemiBold
        }
        Text {
            anchors.baseline: parent.children[0].baseline
            text: root.unit
            color: root.valueColor
            opacity: 0.82
            font.family: T.StyleManager.fontFamily
            font.pixelSize: Math.max(16, root.valueSize * 0.52)
        }
    }
}
