import QtQuick
import "../../../state" as S
import "../../../style" as T

// Compteur de vitesse & Tachymètre combiné 3D Hypercar — Apex Cockpit Instrument
Item {
    id: root
    implicitWidth: 540
    implicitHeight: 540

    property real speed:    S.UiState.speed
    property real maxSpeed: S.UiState.maxSpeed > 0 ? S.UiState.maxSpeed : 250
    property real rpm:      S.UiState.rpm
    property real maxRpm:   S.UiState.maxRpm > 0 ? S.UiState.maxRpm : 7000
    property real redline:  S.UiState.redlineRpm > 0 ? S.UiState.redlineRpm : 6500
    property real rpmRatio: Math.min(1.0, Math.max(0, rpm / maxRpm))
    property bool isRedline: S.UiState.redline

    // Interpolation fluide 60 FPS
    property real animSpeed: speed
    Behavior on animSpeed { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

    property real animRpm: rpm
    Behavior on animRpm { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

    // Pulsation dynamique liée au RPM
    property real pulseScale: 1.0
    property real pulsePeriod: Math.max(200, 1500 - rpmRatio * 1250)

    SequentialAnimation on pulseScale {
        running: speed > 1 || rpm > 1000
        loops: Animation.Infinite
        NumberAnimation { to: 1.025; duration: root.pulsePeriod * 0.45; easing.type: Easing.InOutSine }
        NumberAnimation { to: 1.000; duration: root.pulsePeriod * 0.55; easing.type: Easing.InOutSine }
    }

    // Phase de respiration lumineuse continue
    property real glowPhase: 0.0
    SequentialAnimation on glowPhase {
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: Math.PI * 2; duration: 3000; easing.type: Easing.Linear }
    }

    // ── Cadran de dessin Canvas 3D ────────────────────────────────────────────
    Canvas {
        id: arcCanvas
        anchors.fill: parent
        renderStrategy: Canvas.Cooperative

        property real animSpeed:  root.animSpeed
        property real animRpm:    root.animRpm
        property real maxSpeed:   root.maxSpeed
        property real maxRpm:     root.maxRpm
        property real redline:    root.redline
        property real rpmRatio:   root.rpmRatio
        property real glowPhase:  root.glowPhase
        property bool isRedline:  root.isRedline

        onAnimSpeedChanged: requestPaint()
        onAnimRpmChanged:   requestPaint()
        onGlowPhaseChanged: requestPaint()
        onIsRedlineChanged: requestPaint()

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var w = width, h = height

            // Protection absolue contre les dimensions nulles ou négatives
            if (w < 60 || h < 60) return

            var cx = w * 0.5
            var cy = h * 0.5
            var maxR = Math.min(w, h) * 0.5 - 12
            if (maxR < 20) return

            var speedRatio = Math.min(1.0, Math.max(0, animSpeed / Math.max(1, maxSpeed)))
            var curRpmRatio = Math.min(1.0, Math.max(0, animRpm / Math.max(1, maxRpm)))
            var redlineRatio = Math.min(1.0, Math.max(0, redline / Math.max(1, maxRpm)))

            // Angles : Arc de 135° à 405° (270° de balayage)
            var startDeg = 135
            var totalDeg = 270
            var startRad = (startDeg * Math.PI) / 180
            var totalRad = (totalDeg * Math.PI) / 180

            var speedFillRad = startRad + speedRatio * totalRad
            var rpmFillRad   = startRad + curRpmRatio * totalRad
            var fullRad      = startRad + totalRad

            var acc = T.StyleManager.accent
            var ar = acc.r, ag = acc.g, ab = acc.b

            // ── 1. Cerclage extérieur 3D biseauté & fond concave ──────────────
            var outerGrad = ctx.createRadialGradient(cx, cy, maxR * 0.6, cx, cy, maxR)
            outerGrad.addColorStop(0.0, "#08101C")
            outerGrad.addColorStop(0.7, "#040912")
            outerGrad.addColorStop(0.95, "#0B1422")
            outerGrad.addColorStop(1.0, Qt.rgba(0.15, 0.35, 0.60, 0.4))
            ctx.fillStyle = outerGrad
            ctx.beginPath()
            ctx.arc(cx, cy, maxR, 0, Math.PI * 2)
            ctx.fill()

            // Bague extérieure métallique fine
            ctx.strokeStyle = Qt.rgba(0.2, 0.45, 0.7, 0.35)
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.arc(cx, cy, maxR - 1, 0, Math.PI * 2)
            ctx.stroke()

            // ── 2. Piste extérieure Tachymètre (RPM Arc) ──────────────────────
            var rpmR = maxR - 14
            if (rpmR > 10) {
                // Track de fond RPM
                ctx.beginPath()
                ctx.arc(cx, cy, rpmR, startRad, fullRad, false)
                ctx.strokeStyle = Qt.rgba(0.06, 0.12, 0.20, 0.85)
                ctx.lineWidth = 8
                ctx.lineCap = "round"
                ctx.stroke()

                // Arc actif RPM avec dégradé
                if (curRpmRatio > 0.005) {
                    var rpmGrad = ctx.createLinearGradient(cx - rpmR, cy, cx + rpmR, cy)
                    rpmGrad.addColorStop(0.00, "#00E5FF")
                    rpmGrad.addColorStop(0.65, "#00FF88")
                    rpmGrad.addColorStop(0.85, "#FFB300")
                    rpmGrad.addColorStop(1.00, "#FF1744")

                    ctx.beginPath()
                    ctx.arc(cx, cy, rpmR, startRad, rpmFillRad, false)
                    ctx.strokeStyle = rpmGrad
                    ctx.lineWidth = 8
                    ctx.lineCap = "round"
                    ctx.stroke()
                }
            }

            // ── 3. Piste principale Vitesse (Speedometer Arc) ──────────────────
            var speedR = maxR - 32
            if (speedR > 15) {
                // Track de fond Vitesse
                ctx.beginPath()
                ctx.arc(cx, cy, speedR, startRad, fullRad, false)
                ctx.strokeStyle = Qt.rgba(0.04, 0.08, 0.16, 0.95)
                ctx.lineWidth = 16
                ctx.lineCap = "round"
                ctx.stroke()

                // Arc actif Vitesse
                if (speedRatio > 0.003) {
                    var speedGrad = ctx.createLinearGradient(cx - speedR, cy, cx + speedR, cy)
                    if (isRedline) {
                        speedGrad.addColorStop(0.0, "#FF1744")
                        speedGrad.addColorStop(1.0, "#FF5252")
                    } else {
                        speedGrad.addColorStop(0.00, Qt.rgba(ar * 0.5, ag * 0.5, ab, 0.9))
                        speedGrad.addColorStop(0.50, Qt.rgba(ar, ag, ab, 1.0))
                        speedGrad.addColorStop(0.85, "#00F0FF")
                        speedGrad.addColorStop(1.00, "#00FF88")
                    }

                    ctx.beginPath()
                    ctx.arc(cx, cy, speedR, startRad, speedFillRad, false)
                    ctx.strokeStyle = speedGrad
                    ctx.lineWidth = 16
                    ctx.lineCap = "round"
                    ctx.stroke()

                    // Biseau brillant sur le haut de l'arc (effet 3D)
                    ctx.beginPath()
                    ctx.arc(cx, cy, speedR - 3, startRad, speedFillRad, false)
                    ctx.strokeStyle = Qt.rgba(1.0, 1.0, 1.0, 0.28)
                    ctx.lineWidth = 3
                    ctx.stroke()

                    // Tête lumineuse (Plasma Flare Tip)
                    var tipX = cx + speedR * Math.cos(speedFillRad)
                    var tipY = cy + speedR * Math.sin(speedFillRad)
                    var flareR = 22
                    var flareGrad = ctx.createRadialGradient(tipX, tipY, 0, tipX, tipY, flareR)
                    var flareColor = isRedline ? "#FF1744" : "#00F0FF"
                    var flareA = 0.80 + 0.20 * Math.sin(glowPhase)
                    flareGrad.addColorStop(0.0, Qt.rgba(Qt.color(flareColor).r, Qt.color(flareColor).g, Qt.color(flareColor).b, flareA))
                    flareGrad.addColorStop(0.5, Qt.rgba(Qt.color(flareColor).r, Qt.color(flareColor).g, Qt.color(flareColor).b, flareA * 0.35))
                    flareGrad.addColorStop(1.0, "transparent")
                    ctx.fillStyle = flareGrad
                    ctx.beginPath()
                    ctx.arc(tipX, tipY, flareR, 0, Math.PI * 2)
                    ctx.fill()
                }
            }

            // ── 4. Graduations 3D & Chiffres de Vitesse ───────────────────────
            var numTicks = 13 // 0, 20, 40 ... 260
            for (var i = 0; i <= numTicks; i++) {
                var tRatio = i / numTicks
                var tickAngle = startRad + tRatio * totalRad
                var isMajor = (i % 2 === 0)
                var tickLen = isMajor ? 14 : 8

                var tickInner = speedR - 14 - tickLen
                var tickOuter = speedR - 14

                if (tickInner > 5) {
                    var tx1 = cx + tickInner * Math.cos(tickAngle)
                    var ty1 = cy + tickInner * Math.sin(tickAngle)
                    var tx2 = cx + tickOuter * Math.cos(tickAngle)
                    var ty2 = cy + tickOuter * Math.sin(tickAngle)

                    var isPassed = tRatio <= speedRatio
                    var isRedZone = tRatio >= 0.85

                    ctx.strokeStyle = isRedZone
                        ? Qt.rgba(1.0, 0.2, 0.2, isPassed ? 1.0 : 0.45)
                        : (isPassed ? Qt.rgba(1.0, 1.0, 1.0, 0.95) : Qt.rgba(0.7, 0.85, 1.0, 0.25))
                    ctx.lineWidth = isMajor ? 2.5 : 1.2
                    ctx.beginPath()
                    ctx.moveTo(tx1, ty1)
                    ctx.lineTo(tx2, ty2)
                    ctx.stroke()

                    // Valeurs numériques de vitesse
                    if (isMajor) {
                        var valText = Math.round(tRatio * maxSpeed)
                        var labelR = speedR - 38
                        if (labelR > 10) {
                            var lx = cx + labelR * Math.cos(tickAngle)
                            var ly = cy + labelR * Math.sin(tickAngle)

                            ctx.save()
                            ctx.translate(lx, ly)
                            ctx.fillStyle = isPassed ? "#FFFFFF" : Qt.rgba(0.75, 0.88, 1.0, 0.40)
                            ctx.font = "bold 13px sans-serif"
                            ctx.textAlign = "center"
                            ctx.textBaseline = "middle"
                            ctx.fillText(valText, 0, 0)
                            ctx.restore()
                        }
                    }
                }
            }

            // ── 5. Cœur concave 3D intérieur ───────────────────────────────────
            var innerR = Math.max(10, speedR - 56)
            var innerGlow = ctx.createRadialGradient(cx, cy, 5, cx, cy, innerR)
            innerGlow.addColorStop(0.0, "#0B1626")
            innerGlow.addColorStop(0.6, "#060D17")
            innerGlow.addColorStop(1.0, "#02050A")
            ctx.fillStyle = innerGlow
            ctx.beginPath()
            ctx.arc(cx, cy, innerR, 0, Math.PI * 2)
            ctx.fill()

            // Cerclage intérieur biseauté néon
            ctx.strokeStyle = Qt.rgba(ar, ag, ab, 0.35)
            ctx.lineWidth = 1.5
            ctx.beginPath()
            ctx.arc(cx, cy, innerR, 0, Math.PI * 2)
            ctx.stroke()

            // Halo central subtil
            var pulseA = (0.05 + 0.03 * Math.sin(glowPhase)) * (0.4 + curRpmRatio * 0.6)
            var centerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, innerR * 0.8)
            centerGlow.addColorStop(0.0, Qt.rgba(ar, ag, ab, pulseA * 2.2))
            centerGlow.addColorStop(0.7, Qt.rgba(ar, ag, ab, pulseA * 0.3))
            centerGlow.addColorStop(1.0, "transparent")
            ctx.fillStyle = centerGlow
            ctx.beginPath()
            ctx.arc(cx, cy, innerR * 0.8, 0, Math.PI * 2)
            ctx.fill()
        }
    }

    // ── 6. Chiffre numérique géant haute lisibilité ───────────────────────────
    Item {
        anchors.centerIn: parent
        width: 260
        height: 160

        Column {
            anchors.centerIn: parent
            spacing: -6
            scale: root.pulseScale

            Text {
                id: speedDigits
                anchors.horizontalCenter: parent.horizontalCenter
                text: Math.round(root.speed)
                color: root.isRedline ? "#FF2244" : "#FFFFFF"
                font.pixelSize: 96
                font.weight: Font.Black
                font.letterSpacing: -3.0

                Behavior on color { ColorAnimation { duration: 200 } }
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "KM/H"
                color: Qt.rgba(1.0, 1.0, 1.0, 0.50)
                font.pixelSize: 16
                font.weight: Font.Black
                font.letterSpacing: 4.0
            }
        }
    }

    // ── 7. Badge Rapport de boîte de vitesse (N, R, 1-6) ──────────────────────
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 32
        anchors.horizontalCenter: parent.horizontalCenter
        width: 84
        height: 48
        radius: 12
        color: root.isRedline ? Qt.rgba(1.0, 0.1, 0.1, 0.28) : Qt.rgba(0.06, 0.14, 0.25, 0.90)
        border.width: 2
        border.color: root.isRedline ? "#FF1744" : Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.75)

        Row {
            anchors.centerIn: parent
            spacing: 4

            Text {
                text: S.UiState.gear
                color: root.isRedline ? "#FF1744" : "#FFFFFF"
                font.pixelSize: 26
                font.weight: Font.Black
                Behavior on color { ColorAnimation { duration: 180 } }
            }
        }

        // Lueur flash rouge si rupteur
        SequentialAnimation on opacity {
            running: root.isRedline
            loops: Animation.Infinite
            NumberAnimation { to: 0.35; duration: 150 }
            NumberAnimation { to: 1.00; duration: 150 }
        }
    }

    // ── 8. Régime RPM textuel en bas à droite ─────────────────────────────────
    Text {
        anchors.right: parent.right
        anchors.rightMargin: 42
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 60
        text: Math.round(root.rpm) + " RPM"
        color: root.isRedline ? "#FF1744" : Qt.rgba(1, 1, 1, 0.55)
        font.pixelSize: 14
        font.weight: Font.Bold
        font.letterSpacing: 1.0
    }
}
