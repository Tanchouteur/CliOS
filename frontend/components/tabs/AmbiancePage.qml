import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../../style" as T

Rectangle {
    id: root
    color: T.Theme.bgMain

    // Variables internes pour la roue et le slider
    property real currentHue: 0.05
    property real currentBrightness: 1.0
    property color selectedColor: Qt.hsva(currentHue, 1.0, currentBrightness, 1.0)

    onSelectedColorChanged: T.Theme.main = selectedColor

    // Initialisation au chargement de la page
    Component.onCompleted: {
        // On lit la config (avec précaution si "theme" n'existe pas encore)
        var startColorHex = (bridge.config.theme !== undefined && bridge.config.theme.main !== undefined)
                             ? bridge.config.theme.main
                             : "#ff4400"

        // On convertit le HEX en objet QColor pour extraire la teinte et la luminosité
        var c = Qt.color(startColorHex)
        currentHue = c.hsvHue
        currentBrightness = c.hsvValue
        brightnessSlider.value = currentBrightness
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 30
        anchors.rightMargin: 30
        spacing: 20

        // ----------------------------------------------------
        // 1. HEADER (Bouton Retour + Titre)
        // ----------------------------------------------------
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 50

            MouseArea {
                id: backBtn
                width: 120
                height: parent.height
                cursorShape: Qt.PointingHandCursor
                onClicked: root.StackView.view.pop()

                RowLayout {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Text {
                        text: "←"
                        color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                        font.pixelSize: 28
                    }
                    Text {
                        text: "Retour"
                        color: backBtn.pressed ? T.Theme.unselected : T.Theme.textMain
                        font.pixelSize: 20
                    }
                }
            }

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
        // 2. ROUE CHROMATIQUE (Canvas)
        // ----------------------------------------------------
        // CORRECTION LAYOUT : On enlève le wrapper Item inutile et les anchors
        Item {
            id: wheelContainer
            width: 260
            height: 260
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 20 // Remplace le verticalCenterOffset

            Canvas {
                id: colorCanvas
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d");
                    var cx = width / 2;
                    var cy = height / 2;
                    var radius = 100;
                    var thickness = 30;

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

            Rectangle {
                width: 34; height: 34; radius: 17
                color: "transparent"
                border.color: T.Theme.textMain
                border.width: 3

                x: wheelContainer.width / 2 + 100 * Math.cos(root.currentHue * 2 * Math.PI) - width / 2
                y: wheelContainer.height / 2 + 100 * Math.sin(root.currentHue * 2 * Math.PI) - height / 2
            }

            Rectangle {
                anchors.centerIn: parent
                width: 100; height: 100; radius: 50
                color: root.selectedColor
                border.color: T.Theme.bgDimmed
                border.width: 5

                Rectangle {
                    anchors.fill: parent
                    radius: 50
                    color: "transparent"
                    border.color: Qt.rgba(0,0,0,0.3)
                    border.width: 1
                }
            }
        }

        // ----------------------------------------------------
        // 3. SLIDER DE LUMINOSITÉ (Style Basic)
        // ----------------------------------------------------
        // CORRECTION LAYOUT : On enlève les anchors ici aussi
        ColumnLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true
            Layout.maximumWidth: 500
            Layout.topMargin: 50
            spacing: 15

            Text {
                text: "Intensité lumineuse (" + Math.round(brightnessSlider.value * 100) + "%)"
                color: T.Theme.textDimmed
                font.pixelSize: 16
                Layout.alignment: Qt.AlignHCenter
            }

            Slider {
                id: brightnessSlider
                Layout.fillWidth: true
                from: 0.1
                to: 1.0
                value: 1.0 // La vraie valeur est initialisée dans le Component.onCompleted

                onValueChanged: root.currentBrightness = value

                onPressedChanged: {
                    if (!pressed) {
                        bridge.save_setting("theme.main", root.selectedColor.toString())
                    }
                }

                background: Rectangle {
                    x: brightnessSlider.leftPadding
                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                    implicitWidth: 200
                    implicitHeight: 8
                    width: brightnessSlider.availableWidth
                    height: implicitHeight
                    radius: 4
                    color: T.Theme.bgDimmed

                    Rectangle {
                        width: brightnessSlider.visualPosition * parent.width
                        height: parent.height
                        color: root.selectedColor
                        radius: 4
                        Behavior on color { ColorAnimation { duration: 100 } }
                    }
                }

                handle: Rectangle {
                    x: brightnessSlider.leftPadding + brightnessSlider.visualPosition * (brightnessSlider.availableWidth - width)
                    y: brightnessSlider.topPadding + brightnessSlider.availableHeight / 2 - height / 2
                    implicitWidth: 28
                    implicitHeight: 28
                    radius: 14
                    color: T.Theme.textMain
                    border.color: root.selectedColor
                    border.width: 3
                    Behavior on border.color { ColorAnimation { duration: 100 } }
                }
            }
        }

        Item { Layout.fillHeight: true } // Ressort invisible pour pousser vers le haut
    }
}