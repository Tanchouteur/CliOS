import QtQuick
import "../../../state" as S
import "../../../style" as T

// Barre tachymétrique panoramique F1 / Hypercar — Segments LED dynamiques avec flash Rupteur
Item {
    id: root
    width: parent.width
    height: 14

    property real rpm:      S.UiState.rpm
    property real maxRpm:   S.UiState.maxRpm > 0 ? S.UiState.maxRpm : 7000
    property real redline:  S.UiState.redlineRpm > 0 ? S.UiState.redlineRpm : 6000
    property real ratio:    Math.min(1.0, Math.max(0, rpm / maxRpm))
    property bool isRed:    S.UiState.redline
    property real flashOpacity: 1.0

    // Flash rupteur
    SequentialAnimation on flashOpacity {
        running: root.isRed
        loops: Animation.Infinite
        NumberAnimation { to: 0.30; duration: 130 }
        NumberAnimation { to: 1.00; duration: 130 }
    }
    onIsRedChanged: { if (!isRed) flashOpacity = 1.0 }

    Canvas {
        id: canvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property real ratio:   root.ratio
        property bool isRed:   root.isRed
        property real flash:   root.flashOpacity

        onRatioChanged: requestPaint()
        onIsRedChanged: requestPaint()
        onFlashChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width
            var h = height

            if (w < 20 || h < 4) return

            // Fond noir profond
            ctx.fillStyle = "#03060C"
            ctx.fillRect(0, 0, w, h)

            var numSegments = 64
            var gap = 2
            var segW = (w - (numSegments - 1) * gap) / numSegments
            var activeCount = Math.floor(ratio * numSegments)

            for (var i = 0; i < numSegments; i++) {
                var segRatio = i / numSegments
                var sx = i * (segW + gap)
                var isActive = i <= activeCount

                if (isActive) {
                    var segColor
                    if (segRatio < 0.50) {
                        segColor = "#00E5FF" // Cyan
                    } else if (segRatio < 0.72) {
                        segColor = "#00FF88" // Vert émeraude
                    } else if (segRatio < 0.86) {
                        segColor = "#FFB300" // Ambre
                    } else {
                        segColor = "#FF1744" // Rouge flamme
                    }

                    var alpha = (segRatio >= 0.86 && isRed) ? flash : 0.95
                    ctx.fillStyle = Qt.rgba(
                        Qt.color(segColor).r,
                        Qt.color(segColor).g,
                        Qt.color(segColor).b,
                        alpha
                    )
                } else {
                    // Segment inactif éteint
                    ctx.fillStyle = Qt.rgba(0.08, 0.14, 0.22, 0.35)
                }

                ctx.beginPath()
                ctx.rect(sx, 2, segW, h - 4)
                ctx.fill()
            }

            // Liseré de bas de barre
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.05)
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(0, h)
            ctx.lineTo(w, h)
            ctx.stroke()
        }
    }
}
