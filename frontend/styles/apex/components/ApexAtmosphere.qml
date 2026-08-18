import QtQuick
import "../../../style" as T
import "../../../state" as S

// Fond vivant 3D haute performance — Rendu multi-plans optimisé (25 FPS fixe, faible charge CPU)
Item {
    id: root
    anchors.fill: parent

    property real speedFactor: Math.min(1.0, S.UiState.speed / 160.0)
    property real rpmRatio:    Math.min(1.0, S.UiState.rpm / Math.max(1, S.UiState.maxRpm))

    // ── Plan 1 : Fond statique obsidienne & perspective (dessiné une seule fois) ─
    Canvas {
        id: staticBgCanvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height
            if (w < 40 || h < 40) return

            // Fond obsidienne
            var bg = ctx.createRadialGradient(w * 0.5, h * 0.52, 30, w * 0.5, h * 0.52, w * 0.75)
            bg.addColorStop(0.0, "#08101C")
            bg.addColorStop(0.35, "#040912")
            bg.addColorStop(0.70, "#020509")
            bg.addColorStop(1.00, "#010205")
            ctx.fillStyle = bg
            ctx.fillRect(0, 0, w, h)

            // Lignes de perspective cockpit 3D
            var horizon = h * 0.48
            var vp = w * 0.5
            var acc = T.StyleManager.accent
            var ar = acc.r, ag = acc.g, ab = acc.b

            ctx.save()
            for (var i = -10; i <= 10; i++) {
                if (i === 0) continue
                var dist = Math.abs(i)
                var alpha = Math.max(0.006, 0.032 - dist * 0.0028)
                ctx.strokeStyle = Qt.rgba(ar, ag, ab, alpha)
                ctx.lineWidth = 1
                ctx.beginPath()
                ctx.moveTo(vp + i * 16, horizon)
                ctx.lineTo(vp + i * 190, h + 30)
                ctx.stroke()
            }

            // Anneaux d'horizon elliptiques
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.028)
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.save()
            ctx.translate(vp, horizon + 110)
            ctx.scale(1.0, 0.16)
            ctx.arc(0, 0, w * 0.35, 0, Math.PI * 2)
            ctx.restore()
            ctx.stroke()

            ctx.strokeStyle = Qt.rgba(ar, ag, ab, 0.02)
            ctx.beginPath()
            ctx.save()
            ctx.translate(vp, horizon + 160)
            ctx.scale(1.0, 0.20)
            ctx.arc(0, 0, w * 0.50, 0, Math.PI * 2)
            ctx.restore()
            ctx.stroke()
            ctx.restore()
        }

        Component.onCompleted: requestPaint()
    }

    // ── Plan 2 : Halo d'énergie respirant accéléré par le GPU ──────────────────
    Rectangle {
        id: haloGlow
        anchors.centerIn: parent
        width: 800
        height: 500
        radius: 400
        color: "transparent"

        property real breathPhase: 0.0
        SequentialAnimation on breathPhase {
            loops: Animation.Infinite
            NumberAnimation { from: 0.0; to: Math.PI * 2; duration: 3800; easing.type: Easing.Linear }
        }

        property real pulseOpacity: (0.07 + 0.04 * Math.sin(breathPhase)) * (0.8 + root.rpmRatio * 0.5)

        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
                position: 0.0
                color: Qt.rgba(
                    T.StyleManager.accent.r + root.rpmRatio * 0.5,
                    T.StyleManager.accent.g * (1 - root.rpmRatio * 0.5),
                    T.StyleManager.accent.b * (1 - root.rpmRatio * 0.7),
                    haloGlow.pulseOpacity
                )
            }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // ── Plan 3 : Particules stellaires (Timer à 25 FPS = 40ms, zéro charge inutile) ─
    Canvas {
        id: particleCanvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property var particles: []
        property bool initialized: false

        function initParticles() {
            var arr = []
            for (var i = 0; i < 45; i++) {
                arr.push({
                    x:      Math.random() * width,
                    y:      Math.random() * height,
                    r:      0.6 + Math.random() * 2.0,
                    baseVy: -(0.12 + Math.random() * 0.30),
                    vx:     (Math.random() - 0.5) * 0.15,
                    alpha:  0.15 + Math.random() * 0.45,
                    phi:    Math.random() * Math.PI * 2,
                    layer:  i % 3
                })
            }
            particles = arr
            initialized = true
        }

        Timer {
            id: animTimer
            interval: 40 // 25 FPS optimal
            running: true
            repeat: true
            onTriggered: particleCanvas.requestPaint()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height
            if (w < 40 || h < 40) return

            if (!initialized) initParticles()

            var acc = T.StyleManager.accent
            var ar = acc.r, ag = acc.g, ab = acc.b
            var speedMult = 1.0 + root.speedFactor * 2.0

            for (var k = 0; k < particles.length; k++) {
                var p = particles[k]
                var layerSpeed = (p.layer + 1) * 0.45 * speedMult
                p.y += p.baseVy * layerSpeed
                p.x += p.vx * layerSpeed
                p.phi += 0.04

                if (p.y < -10)  { p.y = h + 10; p.x = Math.random() * w }
                if (p.x < -10)  p.x = w + 10
                if (p.x > w + 10) p.x = -10

                var twinkle = 0.70 + 0.30 * Math.sin(p.phi)
                var a = p.alpha * twinkle
                var size = p.r * (0.85 + 0.30 * (p.layer / 2))

                if (p.layer === 0) {
                    ctx.fillStyle = Qt.rgba(ar, ag, ab, a * 0.40)
                } else if (p.layer === 1) {
                    ctx.fillStyle = Qt.rgba(0.92, 0.96, 1.0, a * 0.50)
                } else {
                    ctx.fillStyle = Qt.rgba(ar * 0.8 + 0.2, ag * 0.8 + 0.2, ab * 0.8 + 0.2, a * 0.80)
                }

                ctx.beginPath()
                ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
                ctx.fill()
            }
        }
    }
}
