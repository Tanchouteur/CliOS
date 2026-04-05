import QtQuick 2.15
import QtQuick.Controls 2.15
import "../../style" as T

Item {
    id: root
    // L'Item prendra automatiquement la place offerte par le StackView

    // --- VARIABLES DE COULEUR ---
    property real currentHue: 0.05
    property real currentBrightness: 1.0
    property color selectedColor: Qt.hsva(currentHue, 1.0, currentBrightness, 1.0)

    onSelectedColorChanged: T.Theme.main = selectedColor

    Component.onCompleted: {
        var startColorHex = (bridge.config.theme !== undefined && bridge.config.theme.main !== undefined)
                             ? bridge.config.theme.main
                             : "#ff4400"
        var c = Qt.color(startColorHex)
        currentHue = c.hsvHue
        currentBrightness = c.hsvValue
        brightnessSlider.value = currentBrightness
    }

    // ----------------------------------------------------
    // 1. HEADER STRICTEMENT ANCRÉ EN HAUT
    // ----------------------------------------------------
    Item {
        id: header
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            topMargin: 20
            leftMargin: 30
            rightMargin: 30
        }
        height: 50

        // Bouton Retour (Gauche)
        MouseArea {
            id: backBtn
            width: 150
            anchors {
                left: parent.left
                top: parent.top
                bottom: parent.bottom
            }
            cursorShape: Qt.PointingHandCursor
            onClicked: root.StackView.view.pop()

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Text {
                    text: "〈"
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 26
                    font.bold: true
                    transform: Translate { x: backBtn.containsMouse ? -4 : 0 }
                    Behavior on transform { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                }
                Text {
                    text: "Retour"
                    color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                    font.pixelSize: 20
                    font.bold: true
                }
            }
        }

        // Titre (Centre)
        Text {
            anchors.centerIn: parent
            text: "ÉCLAIRAGE & AMBIANCE"
            color: T.Theme.textMain
            font.pixelSize: 22
            font.bold: true
            font.letterSpacing: 2
        }
    }

    // ----------------------------------------------------
    // 2. ZONE DES CARTES
    // ----------------------------------------------------
    Row {
        id: cardContainer
        anchors {
            top: header.bottom
            bottom: parent.bottom
            left: parent.left
            right: parent.right
            margins: 30
            topMargin: 20
        }
        spacing: 30

        // --- CARTE GAUCHE : COULEUR PRINCIPALE ---
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)

            // Contenu centré verticalement et horizontalement
            Column {
                anchors.centerIn: parent
                spacing: 40

                Text {
                    text: "COULEUR PRINCIPALE"
                    color: T.Theme.textMain
                    font.pixelSize: 16
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                // --- ROUE CHROMATIQUE (Taille fixe absolue) ---
                Item {
                    id: wheelBox
                    width: 240
                    height: 240
                    anchors.horizontalCenter: parent.horizontalCenter

                    Canvas {
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d");
                            var cx = width / 2;
                            var cy = height / 2;
                            var radius = 100;
                            var thickness = 24;

                            for (var i = 0; i < 360; i++) {
                                ctx.beginPath();
                                ctx.lineWidth = thickness + 2;
                                ctx.arc(cx, cy, radius, (i - 1) * Math.PI / 180, (i + 1) * Math.PI / 180);
                                ctx.strokeStyle = Qt.hsva(i / 360, 1.0, 1.0, 1.0);
                                ctx.stroke();
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.CrossCursor

                        function updateAngle(mouse) {
                            var cx = width / 2;
                            var cy = height / 2;
                            var angle = Math.atan2(mouse.y - cy, mouse.x - cx);
                            if (angle < 0) angle += 2 * Math.PI;
                            root.currentHue = angle / (2 * Math.PI);
                        }

                        onPressed: (mouse) => updateAngle(mouse)
                        onPositionChanged: (mouse) => updateAngle(mouse)
                        onReleased: bridge.save_setting("theme.main", root.selectedColor.toString())
                    }

                    // Curseur tournant (sur le rayon de 100)
                    Rectangle {
                        width: 32; height: 32; radius: 16
                        color: "transparent"
                        border.color: "white"
                        border.width: 4

                        // Centre X/Y = 120. Rayon = 100.
                        x: 120 + 100 * Math.cos(root.currentHue * 2 * Math.PI) - width / 2
                        y: 120 + 100 * Math.sin(root.currentHue * 2 * Math.PI) - height / 2
                    }

                    // Aperçu central
                    Rectangle {
                        anchors.centerIn: parent
                        width: 90; height: 90; radius: 45
                        color: root.selectedColor
                        border.color: T.Theme.bgDimmed
                        border.width: 6
                    }
                }

                // --- SLIDER (Taille fixe absolue) ---
                Column {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 15

                    Text {
                        text: "Luminosité : " + Math.round(brightnessSlider.value * 100) + "%"
                        color: T.Theme.unselected
                        font.pixelSize: 14
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Slider {
                        id: brightnessSlider
                        width: 250 // Largeur fixe blindée
                        height: 40
                        from: 0.1
                        to: 1.0
                        value: 1.0

                        onValueChanged: root.currentBrightness = value
                        onPressedChanged: {
                            if (!pressed) bridge.save_setting("theme.main", root.selectedColor.toString())
                        }

                        background: Rectangle {
                            x: brightnessSlider.leftPadding
                            y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2

                            width: brightnessSlider.availableWidth
                            height: 6
                            radius: 3
                            color: Qt.rgba(0,0,0, 0.4)

                            Rectangle {
                                width: brightnessSlider.visualPosition * parent.width
                                height: parent.height
                                color: root.selectedColor
                                radius: 3
                                Behavior on color { ColorAnimation { duration: 100 } }
                            }
                        }

                        handle: Rectangle {
                            x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                            y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2


                            width: 26
                            height: 26
                            radius: 13
                            color: "white"
                            border.color: root.selectedColor
                            border.width: 4
                            Behavior on border.color { ColorAnimation { duration: 100 } }
                        }
                    }
                }
            }
        }

        // --- CARTE DROITE : COULEUR SECONDAIRE (Bientôt) ---
        Rectangle {
            width: (cardContainer.width - cardContainer.spacing) / 2
            height: parent.height
            color: T.Theme.bgDimmed
            radius: 16
            border.color: Qt.rgba(1, 1, 1, 0.05)
            opacity: 0.4

            Column {
                anchors.centerIn: parent
                spacing: 20

                Text {
                    text: "COULEUR SECONDAIRE"
                    color: T.Theme.textMain
                    font.pixelSize: 16
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Text {
                    text: "Verrouillé\n(Disponible dans une prochaine mise à jour)"
                    color: T.Theme.unselected
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
        }
    }
}