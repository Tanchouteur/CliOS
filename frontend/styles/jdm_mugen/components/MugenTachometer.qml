import QtQuick
import QtQuick.Shapes
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 480
    height: 480

    // Configuration dynamique issue du profil véhicule
    property real configMaxRpm: S.UiState.maxRpm
    property real configRedlineRpm: S.UiState.redlineRpm
    property real currentRpm: S.UiState.rpm

    // Calcul de l'échelle dynamique du cadran (ex: 6000, 7000, 8000, 9000, 10000)
    readonly property int totalUnits: Math.max(5, Math.ceil(configMaxRpm / 1000))
    readonly property real dialMaxRpm: totalUnits * 1000
    readonly property real redlineRpm: configRedlineRpm > 0 ? configRedlineRpm : dialMaxRpm * 0.88

    // 0: Trip A, 1: Trip B, 2: Odomètre Total
    property int tripMode: 0

    // Position directe : aucune interpolation afin de ne jamais retarder l'aiguille.
    readonly property real rpmRatio: Math.max(0.0, Math.min(1.0, currentRpm / dialMaxRpm))
    // 225° = 7h30 (bas-gauche), 495° = 4h30 (bas-droite) -> 270° de débattement
    readonly property real startAngleDeg: 225
    readonly property real spanAngleDeg: 270
    readonly property real needleAngleDeg: (startAngleDeg - 360) + spanAngleDeg * rpmRatio
    property real previousNeedleAngleDeg: needleAngleDeg
    property real motionTrailOffset: 0.0
    property real motionTrailOpacity: 0.0

    onNeedleAngleDegChanged: {
        const delta = needleAngleDeg - previousNeedleAngleDeg
        previousNeedleAngleDeg = needleAngleDeg
        if (Math.abs(delta) < 0.12) return
        motionTrailOffset = Math.max(-16, Math.min(16, delta))
        motionTrailOpacity = Math.min(0.48, 0.10 + Math.abs(delta) * 0.035)
        trailFade.restart()
    }

    NumberAnimation {
        id: trailFade
        target: root
        property: "motionTrailOpacity"
        to: 0.0
        duration: 105
        easing.type: Easing.OutQuad
    }

    // Redessine le cadran automatiquement si le profil ou les limites changent
    onDialMaxRpmChanged: dialCanvas.requestPaint()
    onRedlineRpmChanged: dialCanvas.requestPaint()

    Connections {
        target: S.UiState
        function onConfigChanged() { dialCanvas.requestPaint() }
    }

    // =========================================================================
    // 1. FOND DE CADRAN BLANC MUGEN & GRADUATIONS DYNAMIQUES
    // =========================================================================
    Canvas {
        id: dialCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject
        renderStrategy: Canvas.Threaded

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()

            const cx = width / 2
            const cy = height / 2
            const outerRadius = Math.min(cx, cy) - 6

            // --- A. Bague extérieure biseautée automobile (Métal foncé usiné) ---
            const gradBezel = ctx.createLinearGradient(cx - outerRadius, cy - outerRadius, cx + outerRadius, cy + outerRadius)
            gradBezel.addColorStop(0, "#485260")
            gradBezel.addColorStop(0.3, "#232932")
            gradBezel.addColorStop(0.7, "#12151B")
            gradBezel.addColorStop(1, "#363E4A")

            ctx.fillStyle = gradBezel
            ctx.beginPath()
            ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2)
            ctx.fill()

            // Gorge d'ombre noire interne
            const innerBezelRadius = outerRadius - 10
            ctx.fillStyle = "#0D1015"
            ctx.beginPath()
            ctx.arc(cx, cy, innerBezelRadius, 0, Math.PI * 2)
            ctx.fill()

            // Bague fine métallique
            const rimRadius = innerBezelRadius - 3
            ctx.strokeStyle = "#5A6575"
            ctx.lineWidth = 1.8
            ctx.beginPath()
            ctx.arc(cx, cy, rimRadius, 0, Math.PI * 2)
            ctx.stroke()

            // --- B. Fond de cadran blanc satiné Mugen ---
            const faceRadius = rimRadius - 4
            const gradFace = ctx.createRadialGradient(cx, cy, 20, cx, cy, faceRadius)
            gradFace.addColorStop(0, "#FFFFFF")
            gradFace.addColorStop(0.7, "#F7F9FA")
            gradFace.addColorStop(1, "#E9EEF3")

            ctx.fillStyle = gradFace
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Ombre portée interne sur le pourtour du cadran
            const gradInnerShadow = ctx.createRadialGradient(cx, cy, faceRadius - 16, cx, cy, faceRadius)
            gradInnerShadow.addColorStop(0, "rgba(0,0,0,0)")
            gradInnerShadow.addColorStop(1, "rgba(0,0,0,0.22)")
            ctx.fillStyle = gradInnerShadow
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Cercle concentrique fin
            const trackRadius = faceRadius - 32
            ctx.strokeStyle = "#D2D9E2"
            ctx.lineWidth = 1.2
            ctx.beginPath()
            ctx.arc(cx, cy, trackRadius, 0, Math.PI * 2)
            ctx.stroke()

            // --- C. Secteur Zone Rouge Dynamique (Calculé depuis redline_rpm) ---
            const redStartRatio = Math.max(0.0, Math.min(1.0, root.redlineRpm / root.dialMaxRpm))
            const redEndRatio = 1.0
            const redStartAngleRad = (root.startAngleDeg + root.spanAngleDeg * redStartRatio - 90) * Math.PI / 180
            const redEndAngleRad = (root.startAngleDeg + root.spanAngleDeg * redEndRatio - 90) * Math.PI / 180

            // Bloc rouge plein / hachuré de zone critique
            ctx.fillStyle = "#EA2828"
            ctx.beginPath()
            ctx.arc(cx, cy, trackRadius + 14, redStartAngleRad, redEndAngleRad, false)
            ctx.arc(cx, cy, trackRadius - 16, redEndAngleRad, redStartAngleRad, true)
            ctx.closePath()
            ctx.fill()

            // Motif de hachures blanches dans la zone rouge
            ctx.strokeStyle = "#FFFFFF"
            ctx.lineWidth = 2.0
            const hatchCount = Math.max(6, Math.round((redEndRatio - redStartRatio) * 35))
            for (let h = 0; h <= hatchCount; h++) {
                const hRatio = redStartRatio + (h / hatchCount) * (redEndRatio - redStartRatio)
                const hAngleRad = (root.startAngleDeg + root.spanAngleDeg * hRatio - 90) * Math.PI / 180
                const hCos = Math.cos(hAngleRad)
                const hSin = Math.sin(hAngleRad)
                ctx.beginPath()
                ctx.moveTo(cx + hCos * (trackRadius - 14), cy + hSin * (trackRadius - 14))
                ctx.lineTo(cx + hCos * (trackRadius + 12), cy + hSin * (trackRadius + 12))
                ctx.stroke()
            }

            // --- D. Graduations & Chiffres 0 à N (Dynamiques) ---
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"

            for (let i = 0; i <= root.totalUnits; i++) {
                const ratio = i / root.totalUnits
                const angleDeg = root.startAngleDeg + root.spanAngleDeg * ratio
                const angleRad = (angleDeg - 90) * Math.PI / 180
                const cos = Math.cos(angleRad)
                const sin = Math.sin(angleRad)

                const isRed = (i * 1000) >= root.redlineRpm

                // Trait majeur
                const t1 = trackRadius - 18
                const t2 = trackRadius + 14
                ctx.strokeStyle = isRed ? "#FFFFFF" : "#1A202C"
                ctx.lineWidth = 3.5
                ctx.beginPath()
                ctx.moveTo(cx + cos * t1, cy + sin * t1)
                ctx.lineTo(cx + cos * t2, cy + sin * t2)
                ctx.stroke()

                // Numéro (Police sport italique Mugen)
                const numR = trackRadius - 40
                const nx = cx + cos * numR
                const ny = cy + sin * numR

                ctx.save()
                ctx.translate(nx, ny)
                ctx.font = "italic bold 32px 'Arial', 'Helvetica Neue', sans-serif"
                ctx.fillStyle = isRed ? "#E61E1E" : "#181D26"
                ctx.fillText(i.toString(), 0, 0)
                ctx.restore()

                // Traits mineurs (4 subdivisions entre chaque unité = pas de 200 tr/min)
                if (i < root.totalUnits) {
                    for (let m = 1; m <= 4; m++) {
                        const mRatio = (i + m * 0.2) / root.totalUnits
                        const mVal = (i + m * 0.2) * 1000
                        const mAngleRad = (root.startAngleDeg + root.spanAngleDeg * mRatio - 90) * Math.PI / 180
                        const mCos = Math.cos(mAngleRad)
                        const mSin = Math.sin(mAngleRad)
                        const isSubRed = mVal >= root.redlineRpm

                        const mt1 = trackRadius - (m === 2 ? 12 : 8)
                        const mt2 = trackRadius + (m === 2 ? 10 : 6)
                        ctx.strokeStyle = isSubRed ? "#FFFFFF" : "#4A5568"
                        ctx.lineWidth = (m === 2 ? 2.2 : 1.4)
                        ctx.beginPath()
                        ctx.moveTo(cx + mCos * mt1, cy + mSin * mt1)
                        ctx.lineTo(cx + mCos * mt2, cy + mSin * mt2)
                        ctx.stroke()
                    }
                }
            }

            // --- E. Inscription centrale "x1000r/min" ---
            ctx.font = "14px 'Arial', sans-serif"
            ctx.fillStyle = "#718096"
            ctx.fillText("x1000r/min", cx, cy - 72)

            // --- F. Rivets de fixation du cadran (Gauche et Droite) ---
            function drawRivet(rx, ry) {
                ctx.fillStyle = "#7F8C9D"
                ctx.beginPath()
                ctx.arc(rx, ry, 6.5, 0, Math.PI * 2)
                ctx.fill()
                ctx.fillStyle = "#1E242D"
                ctx.beginPath()
                ctx.arc(rx, ry, 3.5, 0, Math.PI * 2)
                ctx.fill()
                ctx.fillStyle = "#CBD5E1"
                ctx.beginPath()
                ctx.arc(rx - 1, ry - 1, 1.2, 0, Math.PI * 2)
                ctx.fill()
            }

            drawRivet(cx - 105, cy + 24)
            drawRivet(cx + 105, cy + 24)
        }
    }

    // =========================================================================
    // 2. SHIFT LIGHT / FLASH ZONE ROUGE (Indicateur Lumineux Course)
    // =========================================================================
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 28
        width: 60
        height: 12
        radius: 6
        visible: S.UiState.redline || root.currentRpm >= root.redlineRpm
        color: "#FF2B1C"
        border.width: 1.5
        border.color: "#FFFFFF"

        SequentialAnimation on opacity {
            running: parent.visible
            loops: Animation.Infinite
            NumberAnimation { from: 1.0; to: 0.2; duration: 120 }
            NumberAnimation { from: 0.2; to: 1.0; duration: 120 }
        }
    }

    // =========================================================================
    // 3. ÉCRAN LCD NUMÉRIQUE INTÉGRÉ AU CADRAN (Trip / Odomètre / Conso)
    // =========================================================================
    Rectangle {
        id: lcdDisplay
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 + 100
        width: 176
        height: 32
        radius: 4
        color: "#080B0F"
        border.width: 1.5
        border.color: "#3A4555"

        // Fond avec reflet vitre LCD
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1.5
            radius: 3
            color: "#0E1318"

            Row {
                anchors.centerIn: parent
                spacing: 8

                // Label du mode LCD (Trip a / Trip b / Odo)
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.tripMode === 0 ? "Trip a" : (root.tripMode === 1 ? "Trip b" : "ODO")
                    color: "#A0B2C6"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 11
                    font.bold: true
                }

                // Valeur kilométrique
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: {
                        let val = 0
                        if (root.tripMode === 0) val = S.UiState.tripA
                        else if (root.tripMode === 1) val = S.UiState.tripB
                        else val = S.UiState.odometer

                        let str = Math.round(val).toString()
                        while (str.length < 6) str = "0" + str
                        return str + " km"
                    }
                    color: "#D8E4F0"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 14
                    font.bold: true
                    font.letterSpacing: 1.2
                }
            }
        }

        // Clic pour basculer d'affichage (Trip A / Trip B / Odomètre)
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.tripMode = (root.tripMode + 1) % 3
            }
        }
    }

    // =========================================================================
    // 4. AIGUILLE ROUGE FLUO MUGEN (Rotation Matérielle GPU Pure)
    // =========================================================================
    // Copies translucides entre l'ancienne et la nouvelle position. La vraie
    // aiguille reste instantanée ; seules ces traces disparaissent rapidement.
    Repeater {
        model: 5
        delegate: Item {
            x: root.width / 2
            y: root.height / 2
            opacity: root.motionTrailOpacity * (1.0 - index * 0.15)
            transform: Rotation {
                origin.x: 0
                origin.y: 0
                angle: root.needleAngleDeg - root.motionTrailOffset * ((index + 1) / 5.0)
            }
            Shape {
                anchors.centerIn: parent
                antialiasing: true
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    fillColor: "#FF3828"
                    strokeColor: "transparent"
                    startX: -7.5; startY: 28
                    PathLine { x: 7.5; y: 28 }
                    PathLine { x: 2.7; y: -174 }
                    PathLine { x: 0; y: -187 }
                    PathLine { x: -2.7; y: -174 }
                    PathLine { x: -7.5; y: 28 }
                }
            }
        }
    }

    Item {
        id: needleItem
        x: parent.width / 2
        y: parent.height / 2
        transform: Rotation {
            origin.x: 0
            origin.y: 0
            angle: root.needleAngleDeg
        }

        // Aiguille profilée sport
        Shape {
            anchors.centerIn: parent
            antialiasing: true
            preferredRendererType: Shape.CurveRenderer

            // Corps principal rouge fluo
            ShapePath {
                fillColor: "#FF2B1C"
                strokeColor: "#D91406"
                strokeWidth: 0.8
                startX: -5.5; startY: 30
                PathLine { x: 5.5;  y: 30 }
                PathLine { x: 1.5;  y: -178 }
                PathLine { x: 0.0;  y: -186 }
                PathLine { x: -1.5; y: -178 }
                PathLine { x: -5.5; y: 30 }
            }

            // Liseré blanc réfléchissant le long de l'aiguille
            ShapePath {
                strokeColor: "#FFFFFF"
                strokeWidth: 1.2
                startX: 0; startY: 10
                PathLine { x: 0; y: -176 }
            }
        }

        // Contrepoids noir bas d'aiguille
        Rectangle {
            x: -4; y: 15
            width: 8; height: 26
            radius: 3
            color: "#181D24"
        }
    }

    // =========================================================================
    // 5. CAPUCHON CENTRAL NOIR MAT USINÉ (Hub Axe Central)
    // =========================================================================
    Rectangle {
        anchors.centerIn: parent
        width: 60
        height: 60
        radius: 30
        color: "#161B22"
        border.width: 2.2
        border.color: "#353F4F"

        // Disque intérieur avec texture concentrique
        Rectangle {
            anchors.centerIn: parent
            width: 44
            height: 44
            radius: 22
            color: "#0E1217"
            border.width: 1.2
            border.color: "#28313E"

            // Point central usiné
            Rectangle {
                anchors.centerIn: parent
                width: 12
                height: 12
                radius: 6
                color: "#202732"
            }
        }
    }
}
