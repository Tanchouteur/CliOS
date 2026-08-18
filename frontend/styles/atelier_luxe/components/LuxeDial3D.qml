import QtQuick
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 440
    height: 440

    property real minValue: 0
    property real maxValue: 250
    property real currentValue: 0
    property real startAngle: 225 // 7h30 (bas-gauche)
    property real spanAngle: 270  // Monte à 12h et finit à 4h30 (bas-droite)
    property real majorStep: 50
    property int minorTicksCount: 4
    property real redlineStartValue: 999999
    property string unitText: ""
    property bool isRightDial: false

    // Valeur amortie pour une aiguille d'une fluidité parfaite
    property real smoothValue: currentValue
    Behavior on smoothValue {
        NumberAnimation {
            duration: 140
            easing.type: Easing.OutCubic
        }
    }

    onSmoothValueChanged: dynamicCanvas.requestPaint()
    onCurrentValueChanged: dynamicCanvas.requestPaint()

    Connections {
        target: T.StyleManager
        function onAccentChanged() {
            staticCanvas.requestPaint()
            dynamicCanvas.requestPaint()
        }
    }

    // =========================================================================
    // COUCHE 1 : FOND STATIQUE MISE EN CACHE GPU (Exécutée 1 seule fois)
    // =========================================================================
    Canvas {
        id: staticCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject
        renderStrategy: Canvas.Threaded

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()

            const cx = width / 2
            const cy = height / 2
            const radius = Math.min(cx, cy) - 6

            // 1. Bague extérieure moletée / cannelée CNC en titane
            const knurlOuter = radius
            const knurlInner = radius - 14
            const totalKnurls = 60

            ctx.fillStyle = "#0B1017"
            ctx.beginPath()
            ctx.arc(cx, cy, knurlOuter, 0, Math.PI * 2)
            ctx.arc(cx, cy, knurlInner, Math.PI * 2, 0, true)
            ctx.fill()

            for (let i = 0; i < totalKnurls; i++) {
                const ka = (i / totalKnurls) * Math.PI * 2
                const cos = Math.cos(ka)
                const sin = Math.sin(ka)
                const lightFactor = Math.max(0.1, (-cos - sin) * 0.5 + 0.5)

                ctx.strokeStyle = Qt.rgba(
                    0.25 + lightFactor * 0.35,
                    0.35 + lightFactor * 0.4,
                    0.45 + lightFactor * 0.45,
                    0.7
                )
                ctx.lineWidth = 1.6
                ctx.beginPath()
                ctx.moveTo(cx + cos * (knurlInner + 1), cy + sin * (knurlInner + 1))
                ctx.lineTo(cx + cos * (knurlOuter - 1), cy + sin * (knurlOuter - 1))
                ctx.stroke()
            }

            // Liseré brillant supérieur spéculaire
            const outerGlint = ctx.createLinearGradient(cx - knurlOuter, cy - knurlOuter, cx + knurlOuter, cy + knurlOuter)
            outerGlint.addColorStop(0, "#7A95B2")
            outerGlint.addColorStop(0.3, "#3A4F66")
            outerGlint.addColorStop(0.7, "#15202E")
            outerGlint.addColorStop(1, "#455E7A")

            ctx.strokeStyle = outerGlint
            ctx.lineWidth = 1.5
            ctx.beginPath()
            ctx.arc(cx, cy, knurlOuter, 0, Math.PI * 2)
            ctx.stroke()

            // 2. Double chanfrein intérieur usiné
            const bevelWidth = 12
            const rBevelOuter = knurlInner
            const rBevelInner = knurlInner - bevelWidth

            const bevelGrad = ctx.createLinearGradient(cx - rBevelOuter, cy - rBevelOuter, cx + rBevelOuter, cy + rBevelOuter)
            bevelGrad.addColorStop(0, "#2C3D52")
            bevelGrad.addColorStop(0.4, "#141C28")
            bevelGrad.addColorStop(0.8, "#090E16")
            bevelGrad.addColorStop(1, "#1D2A3A")

            ctx.fillStyle = bevelGrad
            ctx.beginPath()
            ctx.arc(cx, cy, rBevelOuter, 0, Math.PI * 2)
            ctx.arc(cx, cy, rBevelInner, Math.PI * 2, 0, true)
            ctx.fill()

            // Gorge d'ombre 3D
            ctx.strokeStyle = "#04060A"
            ctx.lineWidth = 2.5
            ctx.beginPath()
            ctx.arc(cx, cy, rBevelInner, 0, Math.PI * 2)
            ctx.stroke()

            // 3. Fond de cadran en obsidienne avec micro-guillochage
            const dialFaceRadius = rBevelInner - 1
            const faceGrad = ctx.createRadialGradient(cx, cy, 30, cx, cy, dialFaceRadius)
            faceGrad.addColorStop(0, "#111826")
            faceGrad.addColorStop(0.65, "#0A0E17")
            faceGrad.addColorStop(1, "#04070B")

            ctx.fillStyle = faceGrad
            ctx.beginPath()
            ctx.arc(cx, cy, dialFaceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Cercles concentriques de guillochage
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.035)
            ctx.lineWidth = 1
            for (let gr = 50; gr < dialFaceRadius - 20; gr += 22) {
                ctx.beginPath()
                ctx.arc(cx, cy, gr, 0, Math.PI * 2)
                ctx.stroke()
            }

            // 4. Piste de base et graduations
            const arcStartRad = (root.startAngle - 90) * Math.PI / 180
            const arcEndRad = (root.startAngle + root.spanAngle - 90) * Math.PI / 180
            const trackRadius = dialFaceRadius - 24

            ctx.strokeStyle = "#1C2738"
            ctx.lineWidth = 4
            ctx.beginPath()
            ctx.arc(cx, cy, trackRadius, arcStartRad, arcEndRad)
            ctx.stroke()

            const range = root.maxValue - root.minValue
            const totalSteps = Math.round(range / root.majorStep)

            ctx.font = "bold 14px '" + T.StyleManager.fontFamily + "', sans-serif"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"

            for (let i = 0; i <= totalSteps; i++) {
                const val = root.minValue + i * root.majorStep
                const tRatio = (val - root.minValue) / range
                const tAngleDeg = root.startAngle + root.spanAngle * tRatio
                const tAngleRad = (tAngleDeg - 90) * Math.PI / 180
                const isRedline = val >= root.redlineStartValue

                const cos = Math.cos(tAngleRad)
                const sin = Math.sin(tAngleRad)

                // Trait majeur
                const p1r = trackRadius - 12
                const p2r = trackRadius + 9

                ctx.strokeStyle = isRedline ? "#FF4555" : "#FFFFFF"
                ctx.lineWidth = 3.2
                ctx.beginPath()
                ctx.moveTo(cx + cos * p1r, cy + sin * p1r)
                ctx.lineTo(cx + cos * p2r, cy + sin * p2r)
                ctx.stroke()

                // Chiffre de graduation
                const numR = trackRadius - 28
                ctx.fillStyle = isRedline ? "#FF4555" : "#E2E8F0"
                ctx.fillText(Math.round(val).toString(), cx + cos * numR, cy + sin * numR)

                // Traits mineurs
                if (i < totalSteps) {
                    for (let m = 1; m <= root.minorTicksCount; m++) {
                        const mVal = val + m * (root.majorStep / (root.minorTicksCount + 1))
                        const mRatio = (mVal - root.minValue) / range
                        const mAngleRad = (root.startAngle + root.spanAngle * mRatio - 90) * Math.PI / 180
                        const mCos = Math.cos(mAngleRad)
                        const mSin = Math.sin(mAngleRad)
                        const mRedline = mVal >= root.redlineStartValue

                        ctx.strokeStyle = mRedline ? "#FF4555" : Qt.rgba(1, 1, 1, 0.45)
                        ctx.lineWidth = 1.6
                        ctx.beginPath()
                        ctx.moveTo(cx + mCos * (trackRadius - 5), cy + mSin * (trackRadius - 5))
                        ctx.lineTo(cx + mCos * (trackRadius + 5), cy + mSin * (trackRadius + 5))
                        ctx.stroke()
                    }
                }
            }
        }
    }

    // =========================================================================
    // COUCHE 2 : COUCHE DYNAMIQUE ULTRA-LÉGÈRE (Arc actif & Aiguille)
    // =========================================================================
    Canvas {
        id: dynamicCanvas
        anchors.fill: parent

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()

            const cx = width / 2
            const cy = height / 2
            const radius = Math.min(cx, cy) - 6
            const knurlInner = radius - 14
            const rBevelInner = knurlInner - 12
            const dialFaceRadius = rBevelInner - 1
            const trackRadius = dialFaceRadius - 24

            const arcStartRad = (root.startAngle - 90) * Math.PI / 180
            const valRatio = Math.max(0, Math.min(1, (root.smoothValue - root.minValue) / (root.maxValue - root.minValue)))
            const valAngleRad = (root.startAngle + root.spanAngle * valRatio - 90) * Math.PI / 180

            // Arc actif coloré
            if (valRatio > 0.005) {
                const activeGrad = ctx.createLinearGradient(
                    cx + Math.cos(arcStartRad) * trackRadius,
                    cy + Math.sin(arcStartRad) * trackRadius,
                    cx + Math.cos(valAngleRad) * trackRadius,
                    cy + Math.sin(valAngleRad) * trackRadius
                )
                activeGrad.addColorStop(0, Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.45))
                activeGrad.addColorStop(1, T.StyleManager.accent)

                ctx.strokeStyle = activeGrad
                ctx.lineWidth = 4.5
                ctx.beginPath()
                ctx.arc(cx, cy, trackRadius, arcStartRad, valAngleRad)
                ctx.stroke()
            }

            // Aiguille 3D avec ombre
            const needleAngleRad = valAngleRad
            const nLen = trackRadius - 3
            const nBaseWidth = 6.5
            const nTipWidth = 1.8

            ctx.save()
            ctx.shadowColor = "rgba(0, 0, 0, 0.75)"
            ctx.shadowBlur = 10
            ctx.shadowOffsetX = 4
            ctx.shadowOffsetY = 6

            const nCos = Math.cos(needleAngleRad)
            const nSin = Math.sin(needleAngleRad)
            const nNormX = -nSin
            const nNormY = nCos

            ctx.fillStyle = T.StyleManager.accent
            ctx.beginPath()
            ctx.moveTo(cx - nCos * 36 + nNormX * nBaseWidth, cy - nSin * 36 + nNormY * nBaseWidth)
            ctx.lineTo(cx + nCos * nLen + nNormX * nTipWidth, cy + nSin * nLen + nNormY * nTipWidth)
            ctx.lineTo(cx + nCos * (nLen + 7), cy + nSin * (nLen + 7))
            ctx.lineTo(cx + nCos * nLen - nNormX * nTipWidth, cy + nSin * nLen - nNormY * nTipWidth)
            ctx.lineTo(cx - nCos * 36 - nNormX * nBaseWidth, cy - nSin * 36 - nNormY * nBaseWidth)
            ctx.closePath()
            ctx.fill()
            ctx.restore()

            // Rainure lumineuse centrale
            ctx.strokeStyle = "#FFFFFF"
            ctx.lineWidth = 1.2
            ctx.beginPath()
            ctx.moveTo(cx + nCos * 20, cy + nSin * 20)
            ctx.lineTo(cx + nCos * (nLen - 4), cy + nSin * (nLen - 4))
            ctx.stroke()
        }
    }
}
