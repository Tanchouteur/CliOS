import QtQuick
import "../../../state" as S
import "../../../style" as T

// Jauge circulaire Arc Canvas haute performance
Item {
    id: root
    implicitWidth: 160
    implicitHeight: 160

    property string label:     ""
    property string unit:      ""
    property real   value:     0
    property real   from:      0
    property real   to:        100
    property real   warningAt: 0.85     // ratio
    property color  baseColor: T.StyleManager.accent
    property real   ratio:     to > from ? Math.min(1.0, Math.max(0, (value - from) / (to - from))) : 0
    property bool   isWarning: ratio >= warningAt && warningAt < 1.0

    // Interpolation fluide de la valeur
    property real animRatio: ratio
    Behavior on animRatio { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }

    Canvas {
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property real animRatio:  root.animRatio
        property bool isWarning:  root.isWarning

        onAnimRatioChanged: requestPaint()
        onIsWarningChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height
            if (w < 30 || h < 30) return

            var cx = w / 2, cy = h / 2
            var r = Math.min(w, h) / 2 - 10
            if (r < 5) return

            var startRad = (220 - 90) * Math.PI / 180
            var totalDeg = 280
            var totalRad = totalDeg * Math.PI / 180
            var fillRad  = startRad + animRatio * totalRad
            var fullRad  = startRad + totalRad

            // Track de fond
            ctx.beginPath()
            ctx.arc(cx, cy, r, startRad, fullRad, false)
            ctx.strokeStyle = Qt.rgba(0.06, 0.13, 0.22, 1.0)
            ctx.lineWidth = 10
            ctx.lineCap = "round"
            ctx.stroke()

            if (animRatio > 0.005) {
                // Arc rempli
                var col = isWarning ? "#FF1744" : root.baseColor
                var grad = ctx.createLinearGradient(0, 0, w, 0)
                grad.addColorStop(0.0, Qt.rgba(Qt.color(col).r * 0.5, Qt.color(col).g * 0.5, Qt.color(col).b, 0.85))
                grad.addColorStop(0.6, Qt.color(col))
                grad.addColorStop(1.0, isWarning ? "#FF6B00" : Qt.color(col))

                ctx.beginPath()
                ctx.arc(cx, cy, r, startRad, fillRad, false)
                ctx.strokeStyle = grad
                ctx.lineWidth = 10
                ctx.lineCap = "round"
                ctx.stroke()

                // Reflet de brillance
                ctx.beginPath()
                ctx.arc(cx, cy, r, startRad, fillRad, false)
                ctx.strokeStyle = Qt.rgba(1.0, 1.0, 1.0, 0.15)
                ctx.lineWidth = 4
                ctx.stroke()
            }

            // Valeur centrale
            ctx.fillStyle = isWarning ? "#FF4444" : "#FFFFFF"
            ctx.font = "bold " + Math.round(w * 0.24) + "px sans-serif"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            var numVal = isFinite(Number(root.value)) ? Number(root.value) : 0
            var displayVal = (root.to <= 200)
                ? numVal.toFixed(0)
                : Math.round(numVal)
            ctx.fillText(displayVal, cx, cy - 6)

            // Unité
            ctx.fillStyle = Qt.rgba(1.0, 1.0, 1.0, 0.60)
            ctx.font = "bold 13px sans-serif"
            ctx.fillText(root.unit, cx, cy + 18)
        }
    }

    // Label
    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 4
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.label.toUpperCase()
        color: Qt.rgba(1.0, 1.0, 1.0, 0.40)
        font.pixelSize: 11
        font.weight: Font.Bold
        font.letterSpacing: 1.5
    }
}
