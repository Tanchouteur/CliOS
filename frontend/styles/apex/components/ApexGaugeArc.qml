import QtQuick
import "../../../state" as S
import "../../../style" as T

// Jauge circulaire Arc Canvas réutilisable
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

    // Animated value for smooth transitions
    property real animRatio: ratio
    Behavior on animRatio { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }

    // Glow phase
    property real glowPhase: 0.0
    SequentialAnimation on glowPhase {
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: Math.PI * 2; duration: 2600; easing.type: Easing.Linear }
    }

    Canvas {
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property real animRatio:  root.animRatio
        property bool isWarning:  root.isWarning
        property real glowPhase:  root.glowPhase

        onAnimRatioChanged: requestPaint()
        onGlowPhaseChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height
            var cx = w / 2, cy = h / 2
            var r = Math.min(w, h) / 2 - 10

            var startRad = (220 - 90) * Math.PI / 180
            var totalDeg = 280
            var totalRad = totalDeg * Math.PI / 180
            var fillRad  = startRad + animRatio * totalRad
            var fullRad  = startRad + totalRad

            // Track
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
                grad.addColorStop(0,   Qt.rgba(Qt.color(col).r * 0.5, Qt.color(col).g * 0.5, Qt.color(col).b, 0.8))
                grad.addColorStop(0.6, Qt.color(col))
                grad.addColorStop(1,   isWarning ? "#FF6B00" : Qt.color(col))

                ctx.beginPath()
                ctx.arc(cx, cy, r, startRad, fillRad, false)
                ctx.strokeStyle = grad
                ctx.lineWidth = 10
                ctx.lineCap = "round"
                ctx.stroke()

                // Reflet
                ctx.beginPath()
                ctx.arc(cx, cy, r, startRad, fillRad, false)
                ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.12)
                ctx.lineWidth = 4
                ctx.stroke()
            }

            // Valeur centrale
            ctx.fillStyle = isWarning ? "#FF4444" : "#FFFFFF"
            ctx.font = "bold " + Math.round(w * 0.20) + "px Arial"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            var numVal = isFinite(Number(root.value)) ? Number(root.value) : 0
            var displayVal = (root.to <= 200)
                ? numVal.toFixed(0)
                : Math.round(numVal)
            ctx.fillText(displayVal, cx, cy - 6)

            // Unité
            ctx.fillStyle = Qt.rgba(1, 1, 1, 0.50)
            ctx.font = "bold 12px Arial"
            ctx.fillText(root.unit, cx, cy + 18)
        }
    }

    // Label
    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.label.toUpperCase()
        color: Qt.rgba(1, 1, 1, 0.32)
        font.pixelSize: 10
        font.weight: Font.Bold
        font.letterSpacing: 1.8
    }
}
