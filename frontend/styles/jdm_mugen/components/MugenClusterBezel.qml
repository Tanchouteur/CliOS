import QtQuick
import QtQuick.Shapes
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    width: 1920
    height: 720

    signal openMenuRequested()
    signal actionRequested(string action)

    // Horloge digitale en direct
    property string timeText: "12:00"
    Timer {
        interval: 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            const d = new Date()
            const hh = String(d.getHours()).padStart(2, '0')
            const mm = String(d.getMinutes()).padStart(2, '0')
            root.timeText = hh + ":" + mm
        }
    }

    // =========================================================================
    // 1. OMBRAGE DE CASQUETTE & VIGNETTAGE PÉRIPHÉRIQUE
    // =========================================================================
    Canvas {
        id: bezelCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject
        renderStrategy: Canvas.Threaded

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()

            const w = width
            const h = height

            // Dégradé supérieur (effet d'ombre de la casquette plongeante)
            const topGlow = ctx.createLinearGradient(0, 0, 0, 180)
            topGlow.addColorStop(0, "rgba(5, 7, 10, 0.95)")
            topGlow.addColorStop(0.5, "rgba(10, 14, 20, 0.45)")
            topGlow.addColorStop(1, "rgba(0, 0, 0, 0)")
            ctx.fillStyle = topGlow
            ctx.fillRect(0, 0, w, 180)

            // Dégradé inférieur
            const botGlow = ctx.createLinearGradient(0, h - 140, 0, h)
            botGlow.addColorStop(0, "rgba(0, 0, 0, 0)")
            botGlow.addColorStop(0.6, "rgba(10, 14, 20, 0.5)")
            botGlow.addColorStop(1, "rgba(5, 7, 10, 0.95)")
            ctx.fillStyle = botGlow
            ctx.fillRect(0, h - 140, w, 140)

            // Dégradés latéraux
            const leftGlow = ctx.createLinearGradient(0, 0, 120, 0)
            leftGlow.addColorStop(0, "rgba(5, 7, 10, 0.8)")
            leftGlow.addColorStop(1, "rgba(0, 0, 0, 0)")
            ctx.fillStyle = leftGlow
            ctx.fillRect(0, 0, 120, h)

            const rightGlow = ctx.createLinearGradient(w - 120, 0, w, 0)
            rightGlow.addColorStop(0, "rgba(0, 0, 0, 0)")
            rightGlow.addColorStop(1, "rgba(5, 7, 10, 0.8)")
            ctx.fillStyle = rightGlow
            ctx.fillRect(w - 120, 0, 120, h)

            // Fixations / Goujons réalistes
            function drawBezelStud(sx, sy) {
                ctx.fillStyle = "#1E2632"
                ctx.beginPath()
                ctx.arc(sx, sy, 14, 0, Math.PI * 2)
                ctx.fill()
                ctx.strokeStyle = "#38475B"
                ctx.lineWidth = 1.6
                ctx.beginPath()
                ctx.arc(sx, sy, 14, 0, Math.PI * 2)
                ctx.stroke()
                ctx.fillStyle = "#0A0D12"
                ctx.beginPath()
                ctx.arc(sx, sy, 7, 0, Math.PI * 2)
                ctx.fill()
            }

            // Goujons visibles dans la casquette (angles inférieurs et entre les compteurs)
            drawBezelStud(60, 560)
            drawBezelStud(1860, 560)
            drawBezelStud(668, 260)
            drawBezelStud(1252, 260)
        }
    }

    // =========================================================================
    // 2. ZONE SUPÉRIEURE GAUCHE : HORLOGE DIGITALE & CLIGNOTANT GAUCHE
    // =========================================================================
    Row {
        x: 370
        y: 80
        spacing: 20

        // Horloge digitale verte/blanche 7 segments (comme "24:38" sur la photo)
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: root.timeText
            color: "#E2F0D9"
            font.family: "Courier New, monospace"
            font.pixelSize: 24
            font.bold: true
            font.letterSpacing: 2.0
        }

        // Flèche Clignotant Gauche (Vert fluo illuminé)
        Item {
            width: 34
            height: 28
            anchors.verticalCenter: parent.verticalCenter

            Shape {
                anchors.centerIn: parent
                ShapePath {
                    fillColor: S.UiState.turnLeftActive ? "#34D399" : "#142A1E"
                    strokeColor: S.UiState.turnLeftActive ? "#6EE7B7" : "#0A1810"
                    strokeWidth: 1.2
                    startX: 0; startY: 14
                    PathLine { x: 14; y: 2 }
                    PathLine { x: 14; y: 8 }
                    PathLine { x: 30; y: 8 }
                    PathLine { x: 30; y: 20 }
                    PathLine { x: 14; y: 20 }
                    PathLine { x: 14; y: 26 }
                    PathLine { x: 0; y: 14 }
                }
            }

            // Halo lumineux quand actif
            Rectangle {
                anchors.centerIn: parent
                width: 44; height: 36
                radius: 18
                visible: S.UiState.turnLeftActive
                color: Qt.rgba(0.2, 0.9, 0.4, 0.25)
            }
        }

        // Indicateur Régulateur / Limiteur de vitesse (REG / LIM)
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            visible: S.UiState.cruiseMode !== "OFF" && S.UiState.cruiseTarget > 0
            width: 86
            height: 26
            radius: 4
            color: S.UiState.cruiseMode === "REG" ? Qt.rgba(0.2, 0.8, 0.4, 0.2) : Qt.rgba(1.0, 0.6, 0.0, 0.2)
            border.width: 1.2
            border.color: S.UiState.cruiseMode === "REG" ? "#34D399" : "#F59E0B"

            Row {
                anchors.centerIn: parent
                spacing: 4
                Text {
                    text: S.UiState.cruiseMode
                    color: S.UiState.cruiseMode === "REG" ? "#34D399" : "#FBBF24"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 11
                    font.bold: true
                }
                Text {
                    text: Math.round(S.UiState.cruiseTarget).toString()
                    color: "#FFFFFF"
                    font.family: "Courier New, monospace"
                    font.pixelSize: 13
                    font.bold: true
                }
            }
        }
    }

    // =========================================================================
    // 3. ZONE SUPÉRIEURE DROITE : CLIGNOTANT DROIT & TEMPÉRATURE EXTÉRIEURE
    // =========================================================================
    Row {
        x: 1370
        y: 80
        spacing: 24

        // Flèche Clignotant Droit (Vert fluo illuminé)
        Item {
            width: 34
            height: 28
            anchors.verticalCenter: parent.verticalCenter

            Shape {
                anchors.centerIn: parent
                ShapePath {
                    fillColor: S.UiState.turnRightActive ? "#34D399" : "#142A1E"
                    strokeColor: S.UiState.turnRightActive ? "#6EE7B7" : "#0A1810"
                    strokeWidth: 1.2
                    startX: 30; startY: 14
                    PathLine { x: 16; y: 2 }
                    PathLine { x: 16; y: 8 }
                    PathLine { x: 0;  y: 8 }
                    PathLine { x: 0;  y: 20 }
                    PathLine { x: 16; y: 20 }
                    PathLine { x: 16; y: 26 }
                    PathLine { x: 30; y: 14 }
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 44; height: 36
                radius: 18
                visible: S.UiState.turnRightActive
                color: Qt.rgba(0.2, 0.9, 0.4, 0.25)
            }
        }

        // Température extérieure ("24 °C" sur la photo)
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: S.UiState.fixed(S.UiState.outsideTemp, 0, "24") + " °C"
            color: "#E2F0D9"
            font.family: "Courier New, monospace"
            font.pixelSize: 22
            font.bold: true
            font.letterSpacing: 2.0
        }
    }

    // =========================================================================
    // 4. BANDEAU DE VOYANTS D'ALERTE AUTOMOBILE (Telltales réalistes)
    // =========================================================================
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 44
        spacing: 14

        // Voyant Feux de croisement / Position
        Rectangle {
            width: 36; height: 26; radius: 4
            color: S.UiState.lightsActive ? Qt.rgba(0.2, 0.85, 0.4, 0.22) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.lightsActive ? "#34D399" : "#1A2230"
            Text { anchors.centerIn: parent; text: "💡"; font.pixelSize: 13; opacity: S.UiState.lightsActive ? 1.0 : 0.2 }
        }

        // Voyant Pleins phares (Bleu)
        Rectangle {
            width: 36; height: 26; radius: 4
            color: S.UiState.highBeamActive ? Qt.rgba(0.2, 0.5, 1.0, 0.3) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.highBeamActive ? "#3B82F6" : "#1A2230"
            Text { anchors.centerIn: parent; text: "🔦"; font.pixelSize: 13; opacity: S.UiState.highBeamActive ? 1.0 : 0.2 }
        }

        // Voyant Préchauffage Diesel (si moteur diesel avec bougies actives)
        Rectangle {
            width: 36; height: 26; radius: 4
            visible: S.UiState.glowPlugActive
            color: Qt.rgba(1.0, 0.6, 0.0, 0.25)
            border.width: 1
            border.color: "#F59E0B"
            Text { anchors.centerIn: parent; text: "➰"; font.pixelSize: 13; color: "#FBBF24" }
        }

        // Voyant Frein à main / STOP
        Rectangle {
            width: 44; height: 26; radius: 4
            color: (S.UiState.handbrakeActive || S.UiState.brakeWarning) ? Qt.rgba(1.0, 0.2, 0.2, 0.25) : "#0B0E14"
            border.width: 1
            border.color: (S.UiState.handbrakeActive || S.UiState.brakeWarning) ? "#EF4444" : "#1A2230"
            Text { anchors.centerIn: parent; text: "STOP"; color: (S.UiState.handbrakeActive || S.UiState.brakeWarning) ? "#FF4D4D" : "#2D3748"; font.pixelSize: 11; font.bold: true }
        }

        // Voyant Pression d'huile
        Rectangle {
            width: 36; height: 26; radius: 4
            color: S.UiState.oilWarning ? Qt.rgba(1.0, 0.2, 0.2, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.oilWarning ? "#EF4444" : "#1A2230"
            Text { anchors.centerIn: parent; text: "🛢️"; font.pixelSize: 13; opacity: S.UiState.oilWarning ? 1.0 : 0.2 }
        }

        // Voyant Batterie / Charge
        Rectangle {
            width: 36; height: 26; radius: 4
            color: S.UiState.batteryWarning ? Qt.rgba(1.0, 0.2, 0.2, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.batteryWarning ? "#EF4444" : "#1A2230"
            Text { anchors.centerIn: parent; text: "🔋"; font.pixelSize: 13; opacity: S.UiState.batteryWarning ? 1.0 : 0.2 }
        }

        // Voyant Moteur (Check Engine / MIL)
        Rectangle {
            width: 40; height: 26; radius: 4
            color: S.UiState.engineWarning ? Qt.rgba(1.0, 0.6, 0.0, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.engineWarning ? "#F59E0B" : "#1A2230"
            Text { anchors.centerIn: parent; text: "CHECK"; color: S.UiState.engineWarning ? "#FBBF24" : "#2D3748"; font.pixelSize: 9; font.bold: true }
        }

        // Voyant ABS
        Rectangle {
            width: 38; height: 26; radius: 4
            color: S.UiState.absWarning ? Qt.rgba(1.0, 0.6, 0.0, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.absWarning ? "#F59E0B" : "#1A2230"
            Text { anchors.centerIn: parent; text: "ABS"; color: S.UiState.absWarning ? "#FBBF24" : "#2D3748"; font.pixelSize: 10; font.bold: true }
        }

        // Voyant ESP
        Rectangle {
            width: 38; height: 26; radius: 4
            color: S.UiState.espWarning ? Qt.rgba(1.0, 0.6, 0.0, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.espWarning ? "#F59E0B" : "#1A2230"
            Text { anchors.centerIn: parent; text: "ESP"; color: S.UiState.espWarning ? "#FBBF24" : "#2D3748"; font.pixelSize: 10; font.bold: true }
        }

        // Voyant Ceinture
        Rectangle {
            width: 36; height: 26; radius: 4
            color: S.UiState.driverUnbelted ? Qt.rgba(1.0, 0.2, 0.2, 0.25) : "#0B0E14"
            border.width: 1
            border.color: S.UiState.driverUnbelted ? "#EF4444" : "#1A2230"
            Text { anchors.centerIn: parent; text: "👤"; font.pixelSize: 13; opacity: S.UiState.driverUnbelted ? 1.0 : 0.2 }
        }

        // Voyant Portes Ouvertes
        Rectangle {
            width: 36; height: 26; radius: 4
            visible: S.UiState.doorOpen
            color: Qt.rgba(1.0, 0.4, 0.0, 0.25)
            border.width: 1
            border.color: "#F97316"
            Text { anchors.centerIn: parent; text: "🚪"; font.pixelSize: 13 }
        }
    }

    // =========================================================================
    // 5. BOUTON MENU TACTILE INTÉGRÉ
    // =========================================================================
    Rectangle {
        id: menuButton
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 14
        width: 240
        height: 48
        radius: 24
        color: "#111722"
        border.width: 1.8
        border.color: T.StyleManager.accent

        // Halo d'accent Mugen
        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: 22
            color: Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.14)
        }

        Row {
            anchors.centerIn: parent
            spacing: 10

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "☰"
                color: T.StyleManager.accent
                font.pixelSize: 17
                font.bold: true
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "MENU & SYSTÈME"
                color: "#FFFFFF"
                font.family: "Arial, sans-serif"
                font.pixelSize: 13
                font.bold: true
                font.letterSpacing: 1.2
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            hoverEnabled: true
            onEntered: menuButton.color = "#182232"
            onExited: menuButton.color = "#111722"
            onClicked: root.openMenuRequested()
        }
    }

    // =========================================================================
    // 6. TIGES / BOUTONS POUSSOIR PHYSIQUES (Bas de casquette)
    // =========================================================================
    // Bouton de remise à zéro Trip gauche (Trip A)
    Rectangle {
        x: 290
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: 18; height: 34; radius: 9
        color: "#1C2430"
        border.width: 1.5; border.color: "#38475C"

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.actionRequested("reset_a")
        }
    }

    // Bouton de remise à zéro Trip droite (Trip B)
    Rectangle {
        x: 1610
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: 18; height: 34; radius: 9
        color: "#1C2430"
        border.width: 1.5; border.color: "#38475C"

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: root.actionRequested("reset_b")
        }
    }
}
