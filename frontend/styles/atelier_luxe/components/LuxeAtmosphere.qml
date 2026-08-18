import QtQuick
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    anchors.fill: parent

    // Propriété de pulsation continue du halo (battement doux)
    property real breathPhase: 0.0

    // Canvas d'ambiance 3D et micro-particules lumineuses
    Canvas {
        id: bgCanvas
        anchors.fill: parent

        property var particles: []
        property bool initialized: false

        function initParticles() {
            particles = []
            for (let i = 0; i < 70; i++) {
                particles.push({
                    x: Math.random() * root.width,
                    y: Math.random() * root.height,
                    radius: 0.7 + Math.random() * 2.0,
                    speedY: -0.12 - Math.random() * 0.38,
                    speedX: (Math.random() - 0.5) * 0.22,
                    alpha: 0.12 + Math.random() * 0.55,
                    pulse: Math.random() * Math.PI * 2,
                    type: i % 5 // 0: Pur Accent, 1: Éclat Lumineux, 2: Teinte Profonde, 3: Diamant Cristallin, 4: Poussière Ambiante
                })
            }
            initialized = true
        }

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const w = width
            const h = height

            if (!initialized) initParticles()

            const acc = T.StyleManager.accent

            // 1. Fond obsidienne profond avec dégradé radial
            const bgGrad = ctx.createRadialGradient(w / 2, h * 0.52, 40, w / 2, h * 0.52, w * 0.78)
            bgGrad.addColorStop(0, "#0F1626")
            bgGrad.addColorStop(0.35, "#0A0E18")
            bgGrad.addColorStop(0.7, "#06080E")
            bgGrad.addColorStop(1, "#030408")
            ctx.fillStyle = bgGrad
            ctx.fillRect(0, 0, w, h)

            // 2. Halo de respiration ambiant (Harmonisé à 100% avec l'accent choisi)
            const pulseIntensity = 0.08 + 0.04 * Math.sin(root.breathPhase)
            const haloGrad = ctx.createRadialGradient(w / 2, h * 0.5, 20, w / 2, h * 0.5, 520)
            haloGrad.addColorStop(0, Qt.rgba(acc.r, acc.g, acc.b, pulseIntensity))
            haloGrad.addColorStop(0.5, Qt.rgba(acc.r * 0.6, acc.g * 0.6, acc.b * 0.6, pulseIntensity * 0.4))
            haloGrad.addColorStop(1, "transparent")
            ctx.fillStyle = haloGrad
            ctx.fillRect(0, 0, w, h)

            // 3. Lignes de fuite et horizon 3D
            ctx.save()
            ctx.lineWidth = 1
            const horizonY = h * 0.46
            const vanishingX = w / 2

            for (let i = -7; i <= 7; i++) {
                if (i === 0) continue
                const startX = vanishingX + i * 150
                const alpha = Math.max(0.01, 0.04 - Math.abs(i) * 0.005)
                ctx.strokeStyle = Qt.rgba(acc.r, acc.g, acc.b, alpha)
                ctx.beginPath()
                ctx.moveTo(vanishingX + i * 18, horizonY)
                ctx.lineTo(startX, h)
                ctx.stroke()
            }

            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.035)
            ctx.beginPath()
            ctx.ellipse(vanishingX, horizonY + 85, w * 0.62, 95, 0, 0, Math.PI * 2)
            ctx.stroke()
            ctx.restore()

            // 4. Dérive continue des 70 micro-particules (Harmonie analogue stricte)
            // Calcul des variations de couleur analogues à partir de l'accent actuel
            const colorPure = Qt.rgba(acc.r, acc.g, acc.b, 1.0)
            const colorLight = Qt.rgba(Math.min(1.0, acc.r * 1.25 + 0.08), Math.min(1.0, acc.g * 1.25 + 0.08), Math.min(1.0, acc.b * 1.25 + 0.08), 1.0)
            const colorDeep = Qt.rgba(acc.r * 0.7, acc.g * 0.7, acc.b * 0.7, 1.0)
            const colorCrystal = Qt.rgba(0.92 + acc.r * 0.08, 0.94 + acc.g * 0.06, 0.98 + acc.b * 0.02, 1.0)
            const colorDust = Qt.rgba(0.12 + acc.r * 0.15, 0.16 + acc.g * 0.15, 0.22 + acc.b * 0.15, 1.0)

            for (let i = 0; i < particles.length; i++) {
                const p = particles[i]
                p.y += p.speedY
                p.x += p.speedX
                p.pulse += 0.035

                if (p.y < -10) {
                    p.y = h + 10
                    p.x = Math.random() * w
                }
                if (p.x < -10) p.x = w + 10
                if (p.x > w + 10) p.x = -10

                const curAlpha = Math.max(0.06, p.alpha * (0.6 + 0.4 * Math.sin(p.pulse)))

                let pColor = colorPure
                if (p.type === 1) pColor = colorLight
                else if (p.type === 2) pColor = colorDeep
                else if (p.type === 3) pColor = colorCrystal
                else if (p.type === 4) pColor = colorDust

                ctx.fillStyle = pColor
                ctx.globalAlpha = curAlpha
                ctx.beginPath()
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
                ctx.fill()
            }
            ctx.globalAlpha = 1.0
        }
    }

    // Timer d'animation continue optimisé (30 FPS régulier, charge CPU minimale)
    Timer {
        interval: 33
        running: true
        repeat: true
        onTriggered: {
            root.breathPhase += 0.045
            bgCanvas.requestPaint()
        }
    }
}
