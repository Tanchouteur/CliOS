import QtQuick
import QtQuick.Layouts
import "../../../state" as S
import "../../../style" as T

// Instrument central panoramique. La profondeur est dessinée en Canvas afin de
// rester fluide sur le Raspberry Pi, sans dépendance 3D ni texture externe.
Item {
    id: root
    implicitWidth: 900
    implicitHeight: 560

    readonly property real rpmRatio: Math.max(0, Math.min(1, S.UiState.rpm / Math.max(1, S.UiState.maxRpm)))
    readonly property bool redline: S.UiState.redline
    property real animatedSpeed: S.UiState.speed
    property real animatedRpm: S.UiState.rpm

    Behavior on animatedSpeed { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
    Behavior on animatedRpm { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

    // Ombre de contact : donne du poids au bloc sans flouter le texte.
    Rectangle {
        anchors.fill: shell
        anchors.topMargin: 14
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        radius: 42
        color: "#B8000000"
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        radius: 38
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.00; color: "#162333" }
            GradientStop { position: 0.035; color: "#0B111A" }
            GradientStop { position: 0.55; color: "#05080D" }
            GradientStop { position: 1.00; color: "#0B1119" }
        }
        border.width: 1
        border.color: "#2D4258"

        // Reflet taillé dans la coque.
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: 22
            height: 1
            color: "#66FFFFFF"
        }

        Canvas {
            id: depthCanvas
            anchors.fill: parent
            anchors.margins: 3
            opacity: 0.92

            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                var w = width, h = height
                if (w < 100 || h < 100) return

                // Halo optique central, volontairement large pour l'écran peu lumineux.
                var glow = ctx.createRadialGradient(w * 0.5, h * 0.43, 0, w * 0.5, h * 0.43, w * 0.48)
                glow.addColorStop(0.0, Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.13))
                glow.addColorStop(0.34, Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, 0.045))
                glow.addColorStop(1.0, "transparent")
                ctx.fillStyle = glow
                ctx.fillRect(0, 0, w, h)

                // Arches en perspective, comme une pièce d'aluminium évidée.
                var layers = [
                    { inset: 34, alpha: 0.22, width: 1.4 },
                    { inset: 66, alpha: 0.16, width: 1.2 },
                    { inset: 102, alpha: 0.11, width: 1.0 }
                ]
                for (var i = 0; i < layers.length; ++i) {
                    var layer = layers[i]
                    var radiusX = w * 0.5 - layer.inset
                    var radiusY = h * 0.57 - layer.inset * 0.42
                    ctx.save()
                    ctx.translate(w * 0.5, h * 0.46)
                    ctx.scale(radiusX, radiusY)
                    ctx.beginPath()
                    ctx.arc(0, 0, 1, Math.PI * 0.08, Math.PI * 0.92)
                    ctx.strokeStyle = Qt.rgba(T.StyleManager.accent.r, T.StyleManager.accent.g, T.StyleManager.accent.b, layer.alpha)
                    ctx.lineWidth = layer.width / Math.max(radiusX, radiusY)
                    ctx.stroke()
                    ctx.restore()
                }

                // Traits de fuite : la 3D reste lisible même lorsque le fond perd du contraste.
                ctx.lineWidth = 1
                for (var j = 0; j < 7; ++j) {
                    var p = j / 6
                    var x = w * (0.16 + p * 0.68)
                    ctx.beginPath()
                    ctx.moveTo(w * 0.5 + (x - w * 0.5) * 0.44, h * 0.63)
                    ctx.lineTo(x, h * 0.87)
                    ctx.strokeStyle = Qt.rgba(0.55, 0.72, 0.88, 0.055 + Math.abs(p - 0.5) * 0.05)
                    ctx.stroke()
                }
            }
        }

        // Bande RPM en retrait, séparée du chiffre de vitesse.
        Item {
            id: rpmBand
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.topMargin: 24
            anchors.leftMargin: 34
            anchors.rightMargin: 34
            height: 68

            RowLayout {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right

                Text {
                    text: "MOTEUR"
                    color: "#DDE8F2"
                    font.pixelSize: 14
                    font.weight: Font.Bold
                    font.letterSpacing: 2.2
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: Math.round(root.animatedRpm) + "  TR/MIN"
                    color: root.redline ? "#FF5964" : "#FFFFFF"
                    font.pixelSize: 17
                    font.weight: Font.Bold
                    font.letterSpacing: 1.0
                }
            }

            ApexRpmStrip {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 20
            }
        }

        // Marque fonctionnelle discrète.
        Row {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 118
            spacing: 10

            Rectangle { width: 34; height: 2; color: T.StyleManager.accent; anchors.verticalCenter: parent.verticalCenter }
            Text {
                text: "APEX  /  VELOCITY"
                color: "#AFC0D0"
                font.pixelSize: 13
                font.weight: Font.Bold
                font.letterSpacing: 3.2
            }
            Rectangle { width: 34; height: 2; color: T.StyleManager.accent; anchors.verticalCenter: parent.verticalCenter }
        }

        // Lecture primaire : extrêmement contrastée et visible des deux sièges.
        Column {
            id: speedReadout
            anchors.horizontalCenter: parent.horizontalCenter
            y: 148
            spacing: -14

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: Math.round(root.animatedSpeed)
                color: root.redline ? "#FF6670" : "#FFFFFF"
                font.pixelSize: 180
                font.weight: Font.Black
                font.letterSpacing: -9
                style: Text.Raised
                styleColor: "#4500B8FF"
                Behavior on color { ColorAnimation { duration: 140 } }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "KM/H"
                color: "#C9D7E4"
                font.pixelSize: 20
                font.weight: Font.Bold
                font.letterSpacing: 6
            }
        }

        // Rapport : position proche de la vitesse pour une lecture périphérique instantanée.
        Rectangle {
            id: gearPill
            anchors.verticalCenter: speedReadout.verticalCenter
            anchors.right: parent.right
            anchors.rightMargin: 58
            width: 112
            height: 132
            radius: 24
            color: root.redline ? "#321018" : "#0C1722"
            border.width: 1
            border.color: root.redline ? "#FF5964" : "#47708F"

            Column {
                anchors.centerIn: parent
                spacing: -2
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "RAPPORT"
                    color: "#93A6B8"
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1.5
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.gear
                    color: root.redline ? "#FF6670" : "#FFFFFF"
                    font.pixelSize: 68
                    font.weight: Font.Black
                }
            }
        }

        // Régulateur à gauche, symétrique au rapport.
        Rectangle {
            anchors.verticalCenter: speedReadout.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 58
            width: 126
            height: 132
            radius: 24
            color: S.UiState.cruiseMode !== "OFF" ? "#0B1C22" : "#0B1118"
            border.width: 1
            border.color: S.UiState.cruiseMode !== "OFF" ? T.StyleManager.accent : "#263849"

            Column {
                anchors.centerIn: parent
                spacing: 3
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.cruiseMode === "OFF" ? "ASSIST." : S.UiState.cruiseMode
                    color: S.UiState.cruiseMode === "OFF" ? "#8FA0B0" : T.StyleManager.accent
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    font.letterSpacing: 1.8
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.cruiseTarget > 0 ? Math.round(S.UiState.cruiseTarget) : "—"
                    color: "#FFFFFF"
                    font.pixelSize: 48
                    font.weight: Font.Black
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: S.UiState.cruiseStatus
                    color: S.UiState.cruiseStatus === "ACTIF" ? "#54E3A5" : "#8495A5"
                    font.pixelSize: 11
                    font.weight: Font.Bold
                    font.letterSpacing: 1.0
                }
            }
        }

        // Socle métrique. Les séparateurs verticaux renforcent l'aspect pièce usinée.
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 28
            height: 92
            radius: 20
            color: "#B30C131C"
            border.width: 1
            border.color: "#24394D"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 0

                Repeater {
                    model: [
                        { label: "PUISSANCE", value: S.UiState.fixed(S.UiState.powerHp, 0, "0"), unit: "ch", accent: true },
                        { label: "COUPLE", value: S.UiState.fixed(S.UiState.torque, 0, "0"), unit: "N·m", accent: false },
                        { label: "ACCÉLÉRATEUR", value: S.UiState.fixed(S.UiState.throttle, 0, "0"), unit: "%", accent: false }
                    ]
                    delegate: Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: modelData.label
                                color: "#9FB0C0"
                                font.pixelSize: 11
                                font.weight: Font.Bold
                                font.letterSpacing: 1.5
                            }
                            Row {
                                anchors.horizontalCenter: parent.horizontalCenter
                                spacing: 5
                                Text {
                                    text: modelData.value
                                    color: modelData.accent ? T.StyleManager.accent : "#FFFFFF"
                                    font.pixelSize: 30
                                    font.weight: Font.Black
                                }
                                Text {
                                    anchors.baseline: parent.children[0].baseline
                                    text: modelData.unit
                                    color: "#9FB0C0"
                                    font.pixelSize: 13
                                    font.weight: Font.Bold
                                }
                            }
                        }

                        Rectangle {
                            visible: index > 0
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            width: 1
                            height: 44
                            color: "#31465A"
                        }
                    }
                }
            }
        }
    }
}
