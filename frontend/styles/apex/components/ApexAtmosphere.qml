import QtQuick
import "../../../style" as T
import "../../../state" as S

// Fond vivant 3D : Particules multi-couches + Halo de respiration + Lignes de fuite dynamiques
Item {
    id: root
    anchors.fill: parent

    // Phase de respiration continue (0 → 2π)
    property real breathPhase: 0.0
    // Facteurs de vitesse et régime
    property real speedFactor: Math.min(1.0, S.UiState.speed / 160.0)
    property real rpmRatio: Math.min(1.0, S.UiState.rpm / Math.max(1, S.UiState.maxRpm))

    SequentialAnimation on breathPhase {
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: Math.PI * 2; duration: 3600; easing.type: Easing.Linear }
    }

    Canvas {
        id: bgCanvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property var particles: []
        property bool initialized: false
        property real phase: root.breathPhase
        property real speedFactor: root.speedFactor
        property real rpmRatio: root.rpmRatio

        onPhaseChanged: requestPaint()

        function initParticles() {
            var arr = []
            for (var i = 0; i < 65; i++) {
                arr.push({
                    x:      Math.random() * width,
                    y:      Math.random() * height,
                    r:      0.6 + Math.random() * 2.4,
                    baseVy: -(0.10 + Math.random() * 0.35),
                    vx:     (Math.random() - 0.5) * 0.18,
                    alpha:  0.15 + Math.random() * 0.55,
                    phi:    Math.random() * Math.PI * 2,
                    layer:  i % 3 // 0=lointain, 1=moyen, 2=proche
                })
            }
            particles = arr
            initialized = true
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width
            var h = height

            if (!initialized) initParticles()

            var acc = T.StyleManager.accent
            var ar = acc.r, ag = acc.g, ab = acc.b

            // ── 1. Fond obsidienne ultra-profond (haute clarté sur écran USB) ─
            var bg = ctx.createRadialGradient(w * 0.5, h * 0.52, 30, w * 0.5, h * 0.52, w * 0.75)
            bg.addColorStop(0.0, "#08101C")
            bg.addColorStop(0.35, "#040912")
            bg.addColorStop(0.7, "#020509")
            bg.addColorStop(1.0, "#010205")
            ctx.fillStyle = bg
            ctx.fillRect(0, 0, w, h)

            // ── 2. Halo d'énergie respirant (harmonisé avec régime et accent) ──
            var pulse = 0.08 + 0.05 * Math.sin(phase)
            var hr = ar + rpmRatio * (1.0 - ar) * 0.7
            var hg = ag * (1.0 - rpmRatio * 0.6)
            var hb = ab * (1.0 - rpmRatio * 0.8)

            var halo = ctx.createRadialGradient(w * 0.5, h * 0.50, 10, w * 0.5, h * 0.50, 560)
            halo.addColorStop(0.0, Qt.rgba(hr, hg, hb, pulse * 1.8))
            halo.addColorStop(0.4, Qt.rgba(hr, hg, hb, pulse * 0.6))
            halo.addColorStop(0.8, Qt.rgba(hr * 0.4, hg * 0.4, hb * 0.4, pulse * 0.15))
            halo.addColorStop(1.0, "transparent")
            ctx.fillStyle = halo
            ctx.fillRect(0, 0, w, h)

            // ── 3. Arches et lignes de perspective 3D (Cockpit View) ───────────
            var horizon = h * 0.48
            var vp = w * 0.5

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

            // Anneaux d'horizon elliptiques (profondeur)
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

            // ── 4. Micro-particules stellaires (3 couches en parallaxe) ────────
            var speedMult = 1.0 + speedFactor * 2.5
            for (var k = 0; k < particles.length; k++) {
                var p = particles[k]
                var layerSpeed = (p.layer + 1) * 0.45 * speedMult
                p.y += p.baseVy * layerSpeed
                p.x += p.vx * layerSpeed
                p.phi += 0.028

                if (p.y < -12) {
                    p.y = h + 12
                    p.x = Math.random() * w
                }
                if (p.x < -12) p.x = w + 12
                if (p.x > w + 12) p.x = -12

                var twinkle = 0.65 + 0.35 * Math.sin(p.phi)
                var a = p.alpha * twinkle
                var size = p.r * (0.85 + 0.35 * (p.layer / 2))

                if (p.layer === 0) {
                    ctx.fillStyle = Qt.rgba(ar, ag, ab, a * 0.45)
                } else if (p.layer === 1) {
                    ctx.fillStyle = Qt.rgba(0.92, 0.96, 1.0, a * 0.55)
                } else {
                    ctx.fillStyle = Qt.rgba(ar * 0.8 + 0.2, ag * 0.8 + 0.2, ab * 0.8 + 0.2, a * 0.85)
                }

                ctx.beginPath()
                ctx.arc(p.x, p.y, size, 0, Math.PI * 2)
                ctx.fill()

                // Halo sur les particules de premier plan
                if (p.layer === 2 && a > 0.32) {
                    var glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, size * 3.5)
                    glow.addColorStop(0.0, Qt.rgba(ar, ag, ab, a * 0.30))
                    glow.addColorStop(1.0, "transparent")
                    ctx.fillStyle = glow
                    ctx.beginPath()
                    ctx.arc(p.x, p.y, size * 3.5, 0, Math.PI * 2)
                    ctx.fill()
                }
            }
        }
    }
}
