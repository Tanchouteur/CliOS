import QtQuick
import "../../../state" as S
import "../../../style" as T

// Jauge carburant haute technologie avec simulation de liquide vivant et micro-bulles ascendantes
Item {
    id: root
    implicitWidth: 320
    implicitHeight: 110

    property real fuelLevel: S.UiState.fuelLevel
    property real maxFuel:   S.UiState.maxFuel
    property real ratio:     maxFuel > 0 ? Math.min(1.0, Math.max(0, fuelLevel / maxFuel)) : 0
    property bool isLow:     S.UiState.lowFuel

    // Phase d'ondulation continue
    property real wavePhase: 0.0
    SequentialAnimation on wavePhase {
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: Math.PI * 2; duration: 2200; easing.type: Easing.Linear }
    }

    Canvas {
        id: waveCanvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property real ratio:     root.ratio
        property real wavePhase: root.wavePhase
        property bool isLow:     root.isLow
        property var bubbles: []
        property bool bubblesInit: false

        onRatioChanged:     requestPaint()
        onWavePhaseChanged: requestPaint()
        onIsLowChanged:     requestPaint()

        function initBubbles() {
            var b = []
            for (var i = 0; i < 8; i++) {
                b.push({
                    x: Math.random() * (width - 20) + 10,
                    y: height - Math.random() * 40,
                    r: 1.0 + Math.random() * 2.2,
                    speed: 0.4 + Math.random() * 0.7,
                    alpha: 0.25 + Math.random() * 0.45
                })
            }
            bubbles = b
            bubblesInit = true
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height
            var pad = 4
            var rr = 10  // border radius

            if (!bubblesInit) initBubbles()

            // ── 1. Conteneur en verre fumé ─────────────────────────────────────
            ctx.beginPath()
            ctx.roundedRect(pad, pad, w - pad*2, h - pad*2, rr, rr)
            ctx.fillStyle = "#070F1A"
            ctx.fill()
            ctx.strokeStyle = isLow
                ? Qt.rgba(1.0, 0.2, 0.1, 0.7)
                : Qt.rgba(0.0, 0.9, 1.0, 0.25)
            ctx.lineWidth = 1.2
            ctx.stroke()

            if (ratio <= 0.005) {
                // Réservoir vide
                ctx.fillStyle = "#FF1744"
                ctx.font = "bold 16px Arial"
                ctx.textAlign = "center"
                ctx.textBaseline = "middle"
                ctx.fillText("RÉSERVOIR VIDE", w / 2, h / 2)
                return
            }

            var fillH = (h - pad*2) * ratio
            var fillY = pad + (h - pad*2) - fillH

            // Couleur liquide : Rouge si bas, Ambre si moyen, Cyan électrique si normal
            var lr, lg, lb
            if (isLow) {
                lr = 1.0; lg = 0.15; lb = 0.20
            } else if (ratio < 0.35) {
                lr = 1.0; lg = 0.70; lb = 0.0
            } else {
                lr = 0.0; lg = 0.90; lb = 1.0
            }

            // Clip vers le bas
            ctx.save()
            ctx.beginPath()
            ctx.roundedRect(pad, fillY, w - pad*2, fillH + rr, rr, rr)
            ctx.clip()

            // ── 2. Dégradé de profondeur du fluide ────────────────────────────
            var grad = ctx.createLinearGradient(0, fillY, 0, h - pad)
            grad.addColorStop(0.0, Qt.rgba(lr, lg, lb, 0.85))
            grad.addColorStop(0.5, Qt.rgba(lr * 0.75, lg * 0.75, lb * 0.75, 0.90))
            grad.addColorStop(1.0, Qt.rgba(lr * 0.5, lg * 0.5, lb * 0.5, 0.95))
            ctx.fillStyle = grad
            ctx.fillRect(pad, fillY, w - pad*2, fillH + rr)

            // ── 3. Micro-bulles ascendantes ───────────────────────────────────
            for (var b = 0; b < bubbles.length; b++) {
                var bub = bubbles[b]
                bub.y -= bub.speed
                if (bub.y < fillY) {
                    bub.y = h - pad - Math.random() * 8
                    bub.x = pad + 10 + Math.random() * (w - pad*2 - 20)
                }

                ctx.fillStyle = Qt.rgba(1.0, 1.0, 1.0, bub.alpha * 0.6)
                ctx.beginPath()
                ctx.arc(bub.x, bub.y, bub.r, 0, Math.PI * 2)
                ctx.fill()
            }

            // ── 4. Surface ondulante avec double vague ─────────────────────────
            ctx.beginPath()
            var waveAmp = 3.5 * (1.0 - ratio * 0.3)
            ctx.moveTo(pad, fillY + waveAmp)
            var step = 5
            for (var x = pad; x <= w - pad; x += step) {
                var wy = fillY + Math.sin((x / (w * 0.22)) * Math.PI * 2 + wavePhase) * waveAmp
                ctx.lineTo(x, wy)
            }
            ctx.lineTo(w - pad, h - pad)
            ctx.lineTo(pad, h - pad)
            ctx.closePath()
            ctx.fillStyle = Qt.rgba(lr, lg, lb, 0.30)
            ctx.fill()

            // Ligne de crête de la vague (Brillance)
            ctx.beginPath()
            ctx.moveTo(pad, fillY)
            for (var x2 = pad; x2 <= w - pad; x2 += step) {
                var wy2 = fillY + Math.sin((x2 / (w * 0.22)) * Math.PI * 2 + wavePhase) * waveAmp
                ctx.lineTo(x2, wy2)
            }
            ctx.strokeStyle = Qt.rgba(1.0, 1.0, 1.0, 0.35)
            ctx.lineWidth = 1.5
            ctx.stroke()

            ctx.restore()

            // ── 5. Texte central haute visibilité ─────────────────────────────
            ctx.fillStyle = isLow ? "#FF5252" : "#FFFFFF"
            ctx.font = "bold 26px Arial"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"
            ctx.fillText(S.UiState.fixed(root.fuelLevel, 1, "—") + " L", w / 2, h * 0.44)

            // Autonomie restante
            var autoVal = (S.UiState.trip && S.UiState.trip.autonomy !== undefined)
                ? Math.round(S.UiState.trip.autonomy)
                : "—"
            ctx.fillStyle = Qt.rgba(1.0, 1.0, 1.0, 0.65)
            ctx.font = "bold 13px Arial"
            ctx.fillText("AUTONOMIE " + autoVal + " KM", w / 2, h * 0.78)
        }
    }

    // Alerte carburant bas pulsante
    SequentialAnimation on opacity {
        running: root.isLow
        loops: Animation.Infinite
        NumberAnimation { to: 0.65; duration: 500 }
        NumberAnimation { to: 1.0; duration: 500 }
    }
}
