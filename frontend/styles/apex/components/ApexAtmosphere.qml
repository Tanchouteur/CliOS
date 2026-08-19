import QtQuick
import "../../../style" as T

Rectangle {
    id: root
    color: "#020407"
    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop { position: 0.0; color: "#0A121D" }
        GradientStop { position: 0.44; color: "#04080D" }
        GradientStop { position: 1.0; color: "#010203" }
    }

    // Halo central statique : plus fiable qu'un fond animé sur l'alimentation USB.
    Canvas {
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var halo = ctx.createRadialGradient(width * 0.5, -40, 0, width * 0.5, -40, width * 0.52)
            halo.addColorStop(0.0, Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.10))
            halo.addColorStop(0.46, Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.035))
            halo.addColorStop(1.0, "transparent")
            ctx.fillStyle = halo
            ctx.fillRect(0, 0, width, height)
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 2
        color: T.StyleManager.accent
        opacity: 0.72
    }
}
