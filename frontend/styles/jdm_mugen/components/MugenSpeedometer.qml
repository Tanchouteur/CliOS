import QtQuick
import QtQuick.Shapes
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 550
    height: 550

    // Configuration dynamique issue du profil véhicule
    property real configMaxSpeed: S.UiState.maxSpeed
    property real currentSpeed: S.UiState.speed

    // Calcul de l'échelle maximale arrondie par pas de 20 (ex: 200, 220, 240, 260)
    readonly property real dialMaxSpeed: Math.max(160, Math.ceil(configMaxSpeed / 20) * 20)
    readonly property int totalMajorSteps: Math.round(dialMaxSpeed / 20)

    // Lissage réactif de la vitesse
    property real smoothSpeed: currentSpeed
    Behavior on smoothSpeed {
        NumberAnimation { duration: 55; easing.type: Easing.OutQuad }
    }

    readonly property real speedRatio: Math.max(0.0, Math.min(1.0, smoothSpeed / dialMaxSpeed))
    // 225° = 7h30 (bas-gauche), 495° = 4h30 (bas-droite) -> 270° de débattement
    readonly property real startAngleDeg: 225
    readonly property real spanAngleDeg: 270
    readonly property real needleAngleDeg: (startAngleDeg - 360) + spanAngleDeg * speedRatio

    // Redessine le cadran automatiquement si le profil ou la vitesse max changent
    onDialMaxSpeedChanged: dialCanvas.requestPaint()

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
            const innerBezelRadius = outerRadius - 11
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
            const gradFace = ctx.createRadialGradient(cx, cy, 25, cx, cy, faceRadius)
            gradFace.addColorStop(0, "#FFFFFF")
            gradFace.addColorStop(0.7, "#F7F9FA")
            gradFace.addColorStop(1, "#E9EEF3")

            ctx.fillStyle = gradFace
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Ombre portée interne sur le pourtour du cadran
            const gradInnerShadow = ctx.createRadialGradient(cx, cy, faceRadius - 18, cx, cy, faceRadius)
            gradInnerShadow.addColorStop(0, "rgba(0,0,0,0)")
            gradInnerShadow.addColorStop(1, "rgba(0,0,0,0.22)")
            ctx.fillStyle = gradInnerShadow
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Cercle concentrique fin
            const trackRadius = faceRadius - 36
            ctx.strokeStyle = "#D2D9E2"
            ctx.lineWidth = 1.2
            ctx.beginPath()
            ctx.arc(cx, cy, trackRadius, 0, Math.PI * 2)
            ctx.stroke()

            // --- C. Graduations & Chiffres 0 à N km/h (Dynamiques) ---
            const stepValue = 20
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"

            for (let i = 0; i <= root.totalMajorSteps; i++) {
                const val = i * stepValue
                const ratio = val / root.dialMaxSpeed
                const angleDeg = root.startAngleDeg + root.spanAngleDeg * ratio
                const angleRad = (angleDeg - 90) * Math.PI / 180
                const cos = Math.cos(angleRad)
                const sin = Math.sin(angleRad)

                // Trait majeur (tous les 20 km/h)
                const t1 = trackRadius - 18
                const t2 = trackRadius + 14
                ctx.strokeStyle = "#1A202C"
                ctx.lineWidth = 3.5
                ctx.beginPath()
                ctx.moveTo(cx + cos * t1, cy + sin * t1)
                ctx.lineTo(cx + cos * t2, cy + sin * t2)
                ctx.stroke()

                // Numéro (Police sport italique Mugen)
                const numR = trackRadius - 44
                const nx = cx + cos * numR
                const ny = cy + sin * numR

                ctx.save()
                ctx.translate(nx, ny)
                ctx.font = "italic bold 31px 'Arial', 'Helvetica Neue', sans-serif"
                ctx.fillStyle = "#181D26"
                ctx.fillText(val.toString(), 0, 0)
                ctx.restore()

                // Traits intermédiaires (10 km/h et 5 km/h)
                if (i < root.totalMajorSteps) {
                    const midRatio = (val + 10) / root.dialMaxSpeed
                    const midAngleRad = (root.startAngleDeg + root.spanAngleDeg * midRatio - 90) * Math.PI / 180
                    const midCos = Math.cos(midAngleRad)
                    const midSin = Math.sin(midAngleRad)

                    ctx.strokeStyle = "#2D3748"
                    ctx.lineWidth = 2.4
                    ctx.beginPath()
                    ctx.moveTo(cx + midCos * (trackRadius - 13), cy + midSin * (trackRadius - 13))
                    ctx.lineTo(cx + midCos * (trackRadius + 10), cy + midSin * (trackRadius + 10))
                    ctx.stroke()

                    // Traits mineurs (intervalles de 5 km/h)
                    const minorSub = [val + 5, val + 15]
                    for (let s = 0; s < minorSub.length; s++) {
                        const sRatio = minorSub[s] / root.dialMaxSpeed
                        const sAngleRad = (root.startAngleDeg + root.spanAngleDeg * sRatio - 90) * Math.PI / 180
                        const sCos = Math.cos(sAngleRad)
                        const sSin = Math.sin(sAngleRad)

                        ctx.strokeStyle = "#718096"
                        ctx.lineWidth = 1.4
                        ctx.beginPath()
                        ctx.moveTo(cx + sCos * (trackRadius - 8), cy + sSin * (trackRadius - 8))
                        ctx.lineTo(cx + sCos * (trackRadius + 6), cy + sSin * (trackRadius + 6))
                        ctx.stroke()
                    }
                }
            }

            // --- D. Inscription "km/h" sous le sommet ---
            ctx.font = "14px 'Arial', sans-serif"
            ctx.fillStyle = "#718096"
            ctx.fillText("km/h", cx, cy - 80)

            // --- E. Logo MUGEN POWER et Calligraphie Kanji 無限 en bas du cadran ---
            const logoY = cy + 108

            ctx.save()
            ctx.font = "bold 32px 'Hiragino Sans', 'Meiryo', 'Noto Sans CJK JP', 'Yu Gothic', sans-serif"
            ctx.fillStyle = "#11161F"
            ctx.textAlign = "center"
            ctx.fillText("無 限", cx, logoY)
            ctx.restore()

            ctx.save()
            ctx.font = "bold 11px 'Arial Black', 'Arial', sans-serif"
            ctx.fillStyle = "#1E242E"
            ctx.textAlign = "center"
            ctx.letterSpacing = "2px"
            ctx.fillText("MUGEN POWER", cx, logoY + 18)
            ctx.restore()

            // --- F. Rivets de fixation du cadran (Gauche et Droite) ---
            function drawRivet(rx, ry) {
                ctx.fillStyle = "#7F8C9D"
                ctx.beginPath()
                ctx.arc(rx, ry, 7.0, 0, Math.PI * 2)
                ctx.fill()
                ctx.fillStyle = "#1E242D"
                ctx.beginPath()
                ctx.arc(rx, ry, 3.8, 0, Math.PI * 2)
                ctx.fill()
                ctx.fillStyle = "#CBD5E1"
                ctx.beginPath()
                ctx.arc(rx - 1, ry - 1, 1.3, 0, Math.PI * 2)
                ctx.fill()
            }

            drawRivet(cx - 120, cy + 10)
            drawRivet(cx + 120, cy + 10)
        }
    }

    // =========================================================================
    // 2. CURSEUR RÉGULATEUR / LIMITEUR (Cruise Target Bug sur la piste de vitesse)
    // =========================================================================
    Item {
        id: cruiseTargetBug
        anchors.fill: parent
        visible: S.UiState.cruiseTarget > 0 && S.UiState.cruiseMode !== "OFF"

        readonly property real targetRatio: Math.max(0.0, Math.min(1.0, S.UiState.cruiseTarget / root.dialMaxSpeed))
        readonly property real targetAngleDeg: root.startAngleDeg + root.spanAngleDeg * targetRatio
        readonly property real targetAngleRad: (targetAngleDeg - 90) * Math.PI / 180

        Rectangle {
            x: (root.width / 2) + Math.cos(cruiseTargetBug.targetAngleRad) * 230 - width / 2
            y: (root.height / 2) + Math.sin(cruiseTargetBug.targetAngleRad) * 230 - height / 2
            width: 14
            height: 14
            radius: 7
            color: S.UiState.cruiseMode === "REG" ? "#34D399" : "#F59E0B"
            border.width: 2
            border.color: "#FFFFFF"
        }
    }

    // =========================================================================
    // 3. AIGUILLE ROUGE FLUO MUGEN (Rotation Matérielle GPU Pure)
    // =========================================================================
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

            // Corps principal rouge fluo
            ShapePath {
                fillColor: "#FF2B1C"
                strokeColor: "#D91406"
                strokeWidth: 0.8
                startX: -6.0; startY: 34
                PathLine { x: 6.0;  y: 34 }
                PathLine { x: 1.6;  y: -212 }
                PathLine { x: 0.0;  y: -222 }
                PathLine { x: -1.6; y: -212 }
                PathLine { x: -6.0; y: 34 }
            }

            // Liseré blanc réfléchissant le long de l'aiguille
            ShapePath {
                strokeColor: "#FFFFFF"
                strokeWidth: 1.4
                startX: 0; startY: 10
                PathLine { x: 0; y: -210 }
            }
        }

        // Contrepoids noir bas d'aiguille
        Rectangle {
            x: -4.5; y: 18
            width: 9; height: 30
            radius: 3
            color: "#181D24"
        }
    }

    // =========================================================================
    // 4. CAPUCHON CENTRAL NOIR MAT USINÉ (Hub Axe Central)
    // =========================================================================
    Rectangle {
        anchors.centerIn: parent
        width: 68
        height: 68
        radius: 34
        color: "#161B22"
        border.width: 2.4
        border.color: "#353F4F"

        // Disque intérieur avec texture concentrique
        Rectangle {
            anchors.centerIn: parent
            width: 50
            height: 50
            radius: 25
            color: "#0E1217"
            border.width: 1.2
            border.color: "#28313E"

            // Point central usiné
            Rectangle {
                anchors.centerIn: parent
                width: 14
                height: 14
                radius: 7
                color: "#202732"
            }
        }
    }
}
