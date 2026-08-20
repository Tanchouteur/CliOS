import QtQuick
import QtQuick.Shapes
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 480
    height: 480

    // Configuration dynamique issue du profil véhicule
    property real fuelLevel: S.UiState.fuelLevel
    property real maxFuel: S.UiState.maxFuel
    property real reservePct: S.UiState.reservePercentage
    property real engineTemp: S.UiState.engineTemp
    property real minTemp: S.UiState.tempMin
    property real maxTemp: S.UiState.tempMax
    property real warnTemp: S.UiState.tempWarning
    property string gear: S.UiState.gear

    // 0: Range (km), 1: Conso Inst (L/100), 2: Niveau Carburant (L), 3: Coût Trajet (€)
    property int lcdMode: 0

    // Lissage fluide anti-clapotis pour l'essence
    property real smoothFuel: fuelLevel
    Behavior on smoothFuel {
        NumberAnimation { duration: 600; easing.type: Easing.OutCubic }
    }

    // Lissage thermique du liquide de refroidissement
    property real smoothTemp: engineTemp
    Behavior on smoothTemp {
        NumberAnimation { duration: 400; easing.type: Easing.OutCubic }
    }

    // Ratios dynamiques (0.0 = Bas / Froid, 1.0 = Plein / Chaud)
    readonly property real fuelRatio: Math.max(0.0, Math.min(1.0, smoothFuel / Math.max(1, maxFuel)))
    readonly property real tempRatio: Math.max(0.0, Math.min(1.0, (smoothTemp - minTemp) / Math.max(1, maxTemp - minTemp)))

    // Aiguille essence (gauche) : +28° (bas = E) à -28° (haut = F)
    readonly property real fuelNeedleAngle: 28 - fuelRatio * 56
    // Aiguille température (droite) : -28° (bas = C) à +28° (haut = H)
    readonly property real tempNeedleAngle: -28 + tempRatio * 56

    onMaxFuelChanged: dialCanvas.requestPaint()
    onReservePctChanged: dialCanvas.requestPaint()
    onMinTempChanged: dialCanvas.requestPaint()
    onMaxTempChanged: dialCanvas.requestPaint()

    Connections {
        target: S.UiState
        function onConfigChanged() { dialCanvas.requestPaint() }
    }

    // =========================================================================
    // 1. FOND DE CADRAN BLANC MUGEN & GRADUATIONS COMBINÉES DYNAMIQUES
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

            // --- A. Bague extérieure biseautée automobile ---
            const gradBezel = ctx.createLinearGradient(cx - outerRadius, cy - outerRadius, cx + outerRadius, cy + outerRadius)
            gradBezel.addColorStop(0, "#485260")
            gradBezel.addColorStop(0.3, "#232932")
            gradBezel.addColorStop(0.7, "#12151B")
            gradBezel.addColorStop(1, "#363E4A")

            ctx.fillStyle = gradBezel
            ctx.beginPath()
            ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2)
            ctx.fill()

            const innerBezelRadius = outerRadius - 10
            ctx.fillStyle = "#0D1015"
            ctx.beginPath()
            ctx.arc(cx, cy, innerBezelRadius, 0, Math.PI * 2)
            ctx.fill()

            const rimRadius = innerBezelRadius - 3
            ctx.strokeStyle = "#5A6575"
            ctx.lineWidth = 1.8
            ctx.beginPath()
            ctx.arc(cx, cy, rimRadius, 0, Math.PI * 2)
            ctx.stroke()

            // --- B. Fond de cadran blanc satiné ---
            const faceRadius = rimRadius - 4
            const gradFace = ctx.createRadialGradient(cx, cy, 20, cx, cy, faceRadius)
            gradFace.addColorStop(0, "#FFFFFF")
            gradFace.addColorStop(0.7, "#F7F9FA")
            gradFace.addColorStop(1, "#E9EEF3")

            ctx.fillStyle = gradFace
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // Ombre portée interne sur le pourtour
            const gradInnerShadow = ctx.createRadialGradient(cx, cy, faceRadius - 16, cx, cy, faceRadius)
            gradInnerShadow.addColorStop(0, "rgba(0,0,0,0)")
            gradInnerShadow.addColorStop(1, "rgba(0,0,0,0.22)")
            ctx.fillStyle = gradInnerShadow
            ctx.beginPath()
            ctx.arc(cx, cy, faceRadius, 0, Math.PI * 2)
            ctx.fill()

            // =================================================================
            // C. JAUGE ESSENCE (GAUCHE) : F (Haut) à E (Bas)
            // =================================================================
            const fuelPivotX = cx - 130
            const fuelPivotY = cy
            const fuelTrackR = 76

            // Angle rad : de -28° (Haut/F) à +28° (Bas/E)
            const fAngleTop = (-28 * Math.PI) / 180
            const fAngleBottom = (28 * Math.PI) / 180

            // Seuil de réserve dynamique issu de la configuration
            const resRatio = Math.max(0.08, Math.min(0.35, root.reservePct))
            const fAngleReserve = fAngleBottom - resRatio * (fAngleBottom - fAngleTop)

            // Arc standard blanc/gris
            ctx.strokeStyle = "#CBD5E1"
            ctx.lineWidth = 1.8
            ctx.beginPath()
            ctx.arc(fuelPivotX, fuelPivotY, fuelTrackR, fAngleTop, fAngleReserve)
            ctx.stroke()

            // Zone réserve rouge dynamique
            ctx.strokeStyle = "#E62020"
            ctx.lineWidth = 4.0
            ctx.beginPath()
            ctx.arc(fuelPivotX, fuelPivotY, fuelTrackR, fAngleReserve, fAngleBottom)
            ctx.stroke()

            // Graduations traits (0%, 25%, 50%, 75%, 100%)
            const fuelTicks = [0.0, 0.25, 0.5, 0.75, 1.0]
            for (let f = 0; f < fuelTicks.length; f++) {
                const ratio = fuelTicks[f]
                const ang = fAngleBottom - ratio * (fAngleBottom - fAngleTop)
                const isE = ratio <= resRatio
                const t1 = fuelTrackR - (f % 2 === 0 ? 10 : 6)
                const t2 = fuelTrackR + (f % 2 === 0 ? 9 : 5)
                ctx.strokeStyle = isE ? "#E62020" : "#1E293B"
                ctx.lineWidth = f % 2 === 0 ? 2.6 : 1.4
                ctx.beginPath()
                ctx.moveTo(fuelPivotX + Math.cos(ang) * t1, fuelPivotY + Math.sin(ang) * t1)
                ctx.lineTo(fuelPivotX + Math.cos(ang) * t2, fuelPivotY + Math.sin(ang) * t2)
                ctx.stroke()
            }

            // Lettres F et E
            ctx.font = "italic bold 17px 'Arial', sans-serif"
            ctx.textAlign = "center"
            ctx.textBaseline = "middle"

            // F (Haut-Gauche)
            ctx.fillStyle = "#181D26"
            ctx.fillText("F", fuelPivotX + Math.cos(fAngleTop - 0.12) * (fuelTrackR + 18), fuelPivotY + Math.sin(fAngleTop - 0.12) * (fuelTrackR + 18))

            // E (Bas-Gauche - Rouge)
            ctx.fillStyle = "#E62020"
            ctx.fillText("E", fuelPivotX + Math.cos(fAngleBottom + 0.12) * (fuelTrackR + 18), fuelPivotY + Math.sin(fAngleBottom + 0.12) * (fuelTrackR + 18))

            // Icône pompe à essence
            const pumpX = cx - 55
            const pumpY = cy - 6
            ctx.fillStyle = S.UiState.lowFuel ? "#E62020" : "#475569"
            ctx.fillRect(pumpX, pumpY - 8, 10, 14)
            ctx.fillRect(pumpX + 10, pumpY - 4, 3, 10)
            ctx.fillStyle = "#FAFAFA"
            ctx.fillRect(pumpX + 2, pumpY - 6, 6, 5)

            // =================================================================
            // D. JAUGE TEMPÉRATURE D'EAU (DROITE) : H (Haut) à C (Bas)
            // =================================================================
            const tempPivotX = cx + 130
            const tempPivotY = cy
            const tempTrackR = 76

            // Angles rad vers la gauche : 180° + 28° = 208° (Haut/H), 180° - 28° = 152° (Bas/C)
            const tAngleTop = (208 * Math.PI) / 180
            const tAngleBottom = (152 * Math.PI) / 180

            // Seuil de surchauffe dynamique issu de la configuration
            const warnRatio = Math.max(0.6, Math.min(0.95, (root.warnTemp - root.minTemp) / Math.max(1, root.maxTemp - root.minTemp)))
            const tAngleWarn = tAngleBottom + warnRatio * (tAngleTop - tAngleBottom)

            // Arc standard
            ctx.strokeStyle = "#CBD5E1"
            ctx.lineWidth = 1.8
            ctx.beginPath()
            ctx.arc(tempPivotX, tempPivotY, tempTrackR, tAngleBottom, tAngleWarn)
            ctx.stroke()

            // Zone surchauffe rouge
            ctx.strokeStyle = "#E62020"
            ctx.lineWidth = 4.0
            ctx.beginPath()
            ctx.arc(tempPivotX, tempPivotY, tempTrackR, tAngleWarn, tAngleTop)
            ctx.stroke()

            // Graduations traits
            const tempTicks = [0.0, 0.25, 0.5, 0.75, 1.0]
            for (let t = 0; t < tempTicks.length; t++) {
                const ratio = tempTicks[t]
                const ang = tAngleBottom + ratio * (tAngleTop - tAngleBottom)
                const isH = ratio >= warnRatio
                const t1 = tempTrackR - (t % 2 === 0 ? 10 : 6)
                const t2 = tempTrackR + (t % 2 === 0 ? 9 : 5)
                ctx.strokeStyle = isH ? "#E62020" : "#1E293B"
                ctx.lineWidth = t % 2 === 0 ? 2.6 : 1.4
                ctx.beginPath()
                ctx.moveTo(tempPivotX + Math.cos(ang) * t1, tempPivotY + Math.sin(ang) * t1)
                ctx.lineTo(tempPivotX + Math.cos(ang) * t2, tempPivotY + Math.sin(ang) * t2)
                ctx.stroke()
            }

            // Lettres H et C
            // H (Haut-Droite - Rouge)
            ctx.fillStyle = "#E62020"
            ctx.fillText("H", tempPivotX + Math.cos(tAngleTop + 0.12) * (tempTrackR + 18), tempPivotY + Math.sin(tAngleTop + 0.12) * (tempTrackR + 18))

            // C (Bas-Droite)
            ctx.fillStyle = "#181D26"
            ctx.fillText("C", tempPivotX + Math.cos(tAngleBottom - 0.12) * (tempTrackR + 18), tempPivotY + Math.sin(tAngleBottom - 0.12) * (tempTrackR + 18))

            // Icône température liquide de refroidissement
            const tempIconX = cx + 45
            const tempIconY = cy - 6
            ctx.fillStyle = S.UiState.hotEngine ? "#E62020" : "#475569"
            ctx.fillRect(tempIconX + 4, tempIconY - 8, 3, 10)
            ctx.beginPath()
            ctx.arc(tempIconX + 5.5, tempIconY + 4, 4.5, 0, Math.PI * 2)
            ctx.fill()
            ctx.strokeStyle = S.UiState.hotEngine ? "#E62020" : "#475569"
            ctx.lineWidth = 1.4
            ctx.beginPath()
            ctx.moveTo(tempIconX - 6, tempIconY + 4)
            ctx.lineTo(tempIconX + 16, tempIconY + 4)
            ctx.stroke()

            // --- Rivets de fixation du cadran (Gauche) ---
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

            drawRivet(cx - 85, cy - 70)
            drawRivet(cx - 85, cy + 70)
        }
    }

    // =========================================================================
    // 2. COLONNE CENTRALE SÉLECTEUR DE VITESSES (Boîte Mécanique vs Automatique)
    // =========================================================================
    readonly property var gearModel: {
        if (S.UiState.isAutomaticGearbox) {
            // Boîte automatique : P R N D D3 2 1
            return [
                { id: "P", label: "P" },
                { id: "R", label: "R" },
                { id: "N", label: "N" },
                { id: "D", label: "D" },
                { id: "D3", label: "D3" },
                { id: "2", label: "2" },
                { id: "1", label: "1" }
            ]
        } else {
            // Boîte manuelle / mécanique : R, N, 1, 2, 3, 4, 5, (6, 7...)
            const totalGears = Math.max(4, Math.min(7, S.UiState.manualGearCount))
            const list = [
                { id: "R", label: "R" },
                { id: "N", label: "N" }
            ]
            for (let i = 1; i <= totalGears; i++) {
                list.push({ id: String(i), label: String(i) })
            }
            return list
        }
    }

    Rectangle {
        id: gearColumn
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 - 130
        width: 38
        height: 215
        radius: 6
        color: "#0B0E13"
        border.width: 1.5
        border.color: "#2C3542"

        Column {
            anchors.centerIn: parent
            spacing: root.gearModel.length > 7 ? 2 : 3

            Repeater {
                model: root.gearModel

                Rectangle {
                    width: 32
                    height: Math.floor((gearColumn.height - 10 - (root.gearModel.length - 1) * (root.gearModel.length > 7 ? 2 : 3)) / root.gearModel.length)
                    radius: 4

                    property bool isActive: {
                        const current = String(root.gear).toUpperCase()
                        if (modelData.id === current) return true
                        if (modelData.id === "R" && (current === "R" || S.UiState.reverseEngaged)) return true
                        if (modelData.id === "N" && (current === "N" || current === "" || current === "0")) return true
                        if (S.UiState.isAutomaticGearbox) {
                            if (current === "3" && modelData.id === "D3") return true
                            if (current === "4" && modelData.id === "D") return true
                            if (current === "5" && modelData.id === "D") return true
                            if (current === "6" && modelData.id === "D") return true
                            if (current === "1" && modelData.id === "1") return true
                            if (current === "2" && modelData.id === "2") return true
                        }
                        return false
                    }

                    color: isActive ? "#FF2B1C" : "transparent"
                    border.width: isActive ? 1.5 : 0
                    border.color: isActive ? "#FFA39B" : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.label
                        color: parent.isActive ? "#FFFFFF" : "#5A687A"
                        font.family: "Arial, sans-serif"
                        font.pixelSize: root.gearModel.length > 7 ? 11 : (modelData.label.length > 1 ? 11 : 13)
                        font.bold: true
                    }
                }
            }
        }
    }

    // =========================================================================
    // 3. AIGUILLE ESSENCE (GAUCHE - Pivote vers le centre)
    // =========================================================================
    Item {
        id: fuelNeedleItem
        x: parent.width / 2 - 130
        y: parent.height / 2
        transform: Rotation {
            origin.x: 0
            origin.y: 0
            angle: root.fuelNeedleAngle
        }

        Shape {
            anchors.verticalCenter: parent.verticalCenter
            ShapePath {
                fillColor: "#FF2B1C"
                strokeColor: "#D91406"
                strokeWidth: 0.8
                startX: -4.0; startY: -2.5
                PathLine { x: 74.0; y: -1.0 }
                PathLine { x: 80.0; y: 0.0 }
                PathLine { x: 74.0; y: 1.0 }
                PathLine { x: -4.0; y: 2.5 }
                PathLine { x: -4.0; y: -2.5 }
            }
            ShapePath {
                strokeColor: "#FFFFFF"
                strokeWidth: 1.0
                startX: 4; startY: 0
                PathLine { x: 76; y: 0 }
            }
        }

        // Capuchon d'axe gauche
        Rectangle {
            anchors.centerIn: parent
            width: 26; height: 26; radius: 13
            color: "#161B22"
            border.width: 1.8; border.color: "#353F4F"
            Rectangle {
                anchors.centerIn: parent
                width: 10; height: 10; radius: 5
                color: "#0E1217"
            }
        }
    }

    // =========================================================================
    // 4. AIGUILLE TEMPÉRATURE D'EAU (DROITE - Pivote vers le centre)
    // =========================================================================
    Item {
        id: tempNeedleItem
        x: parent.width / 2 + 130
        y: parent.height / 2
        transform: Rotation {
            origin.x: 0
            origin.y: 0
            angle: root.tempNeedleAngle
        }

        Shape {
            anchors.verticalCenter: parent.verticalCenter
            ShapePath {
                fillColor: "#FF2B1C"
                strokeColor: "#D91406"
                strokeWidth: 0.8
                startX: 4.0; startY: -2.5
                PathLine { x: -74.0; y: -1.0 }
                PathLine { x: -80.0; y: 0.0 }
                PathLine { x: -74.0; y: 1.0 }
                PathLine { x: 4.0; y: 2.5 }
                PathLine { x: 4.0; y: -2.5 }
            }
            ShapePath {
                strokeColor: "#FFFFFF"
                strokeWidth: 1.0
                startX: -4; startY: 0
                PathLine { x: -76; y: 0 }
            }
        }

        // Capuchon d'axe droit
        Rectangle {
            anchors.centerIn: parent
            width: 26; height: 26; radius: 13
            color: "#161B22"
            border.width: 1.8; border.color: "#353F4F"
            Rectangle {
                anchors.centerIn: parent
                width: 10; height: 10; radius: 5
                color: "#0E1217"
            }
        }
    }

    // =========================================================================
    // 5. ÉCRAN LCD NUMÉRIQUE MULTI-INFO (Autonomie / Conso / Carburant / Coût)
    // =========================================================================
    Rectangle {
        id: rangeLcdDisplay
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height / 2 + 104
        width: 176
        height: 30
        radius: 4
        color: "#080B0F"
        border.width: 1.5
        border.color: "#3A4555"

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1.5
            radius: 3
            color: "#0E1318"

            Row {
                anchors.centerIn: parent
                spacing: 6

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: {
                        if (root.lcdMode === 0) return "range"
                        if (root.lcdMode === 1) return "inst."
                        if (root.lcdMode === 2) return "fuel"
                        return "cost"
                    }
                    color: "#A0B2C6"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 11
                    font.bold: true
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: {
                        if (root.lcdMode === 0) {
                            return Math.round(S.UiState.autonomy).toString() + " km"
                        } else if (root.lcdMode === 1) {
                            return S.UiState.fixed(S.UiState.instantCons, 1, "0.0") + " L"
                        } else if (root.lcdMode === 2) {
                            return S.UiState.fixed(S.UiState.fuelLevel, 1, "0.0") + " L"
                        } else {
                            return S.UiState.fixed(S.UiState.tripCost, 2, "0.00") + " €"
                        }
                    }
                    color: "#D8E4F0"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 13
                    font.bold: true
                    font.letterSpacing: 1.0
                }
            }
        }

        // Clic pour basculer d'affichage multi-info
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                root.lcdMode = (root.lcdMode + 1) % 4
            }
        }
    }
}
