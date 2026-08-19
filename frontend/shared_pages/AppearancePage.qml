import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T

Item {
    id: root
    signal backRequested()

    property real currentHue: {
        const raw = T.StyleManager.rawAccent || "#48B8FF"
        const c = Qt.color(raw)
        return c.hsvHue >= 0 ? c.hsvHue : 0.55
    }

    readonly property color selectedColor: Qt.hsva(currentHue, 0.92, 1.0, 1.0)
    readonly property var quickPresets: ["#0055FF", "#FFCC00", "#FF2A3B", "#38D996", "#FF7A00", "#FFFFFF"]

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 14
        GtPageHeader {
            Layout.fillWidth: true
            title: "Apparence & Ambiance"
            subtitle: "Personnalisation des thèmes graphiques et de l'éclairage d'accent"
            onBackClicked: root.backRequested()
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14

            // Liste horizontale défilable des thèmes graphiques
            ListView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                orientation: ListView.Horizontal
                spacing: 14
                clip: true
                boundsBehavior: Flickable.DragAndOvershootBounds
                model: T.StyleManager.styles

                delegate: GtCard {
                    width: 350
                    height: ListView.view.height
                    title: modelData.label
                    highlighted: T.StyleManager.styleId === modelData.id
                    ColumnLayout {
                        anchors.fill: parent; spacing: 14
                        Text {
                            Layout.fillWidth: true
                            text: modelData.description
                            color: T.StyleManager.textSecondary
                            font.pixelSize: 15
                            wrapMode: Text.WordWrap
                        }
                        Item { Layout.fillHeight: true }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 110
                            radius: T.StyleManager.radiusMedium; color: modelData.palette.background
                            border.width: 1; border.color: T.StyleManager.accent
                            Row {
                                anchors.centerIn: parent; spacing: 14
                                Rectangle { width: 64; height: 12; radius: 6; color: modelData.palette.surfaceRaised }
                                Rectangle { width: 64; height: 12; radius: 6; color: modelData.palette.gaugeTrack }
                                Rectangle { width: 64; height: 12; radius: 6; color: T.StyleManager.accent }
                            }
                        }
                        GtButton {
                            Layout.fillWidth: true
                            text: T.StyleManager.styleId === modelData.id ? "STYLE ACTIF" : "APPLIQUER"
                            primary: T.StyleManager.styleId === modelData.id
                            onClicked: T.StyleManager.selectStyle(modelData.id)
                        }
                    }
                }
            }

            // Carte Roue Chromatique
            GtCard {
                Layout.preferredWidth: 350
                Layout.minimumWidth: 350
                Layout.maximumWidth: 350
                Layout.fillHeight: true
                title: "Couleur d'accent & LEDs"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: "Touchez la roue pour ajuster la teinte du combiné et des bandeaux LED."
                        color: T.StyleManager.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Item { Layout.fillHeight: true }

                    // Roue Chromatique Canvas
                    Item {
                        id: wheelBox
                        Layout.alignment: Qt.AlignHCenter
                        width: 200
                        height: 200

                        Canvas {
                            id: wheelCanvas
                            anchors.fill: parent
                            onPaint: {
                                const ctx = getContext("2d")
                                const cx = width / 2
                                const cy = height / 2
                                const radius = 82
                                const thickness = 22

                                ctx.clearRect(0, 0, width, height)
                                for (let i = 0; i < 360; i += 2) {
                                    ctx.beginPath()
                                    ctx.lineWidth = thickness
                                    ctx.arc(cx, cy, radius, (i - 1) * Math.PI / 180, (i + 2) * Math.PI / 180)
                                    ctx.strokeStyle = Qt.hsva(i / 360, 0.95, 1.0, 1.0)
                                    ctx.stroke()
                                }
                            }
                        }

                        // Curseur sélecteur sur l'anneau
                        Rectangle {
                            width: 26; height: 26; radius: 13
                            color: root.selectedColor
                            border.width: 3
                            border.color: "#FFFFFF"
                            x: (wheelBox.width / 2) + 82 * Math.cos(root.currentHue * 2 * Math.PI) - width / 2
                            y: (wheelBox.height / 2) + 82 * Math.sin(root.currentHue * 2 * Math.PI) - height / 2
                        }

                        // Bulle centrale de prévisualisation
                        Rectangle {
                            anchors.centerIn: parent
                            width: 82; height: 82; radius: 41
                            color: root.selectedColor
                            border.width: 4
                            border.color: "#182232"

                            Column {
                                anchors.centerIn: parent
                                spacing: 1
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "ACCENT"
                                    color: "#FFFFFF"
                                    font.pixelSize: 9
                                    font.bold: true
                                    opacity: 0.85
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: String(root.selectedColor).toUpperCase().substring(0, 7)
                                    color: "#FFFFFF"
                                    font.pixelSize: 11
                                    font.bold: true
                                    font.family: "Monospace"
                                }
                            }
                        }

                        // Zone tactile circulaire
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.CrossCursor

                            function handleTouch(mouse) {
                                const cx = width / 2
                                const cy = height / 2
                                let angle = Math.atan2(mouse.y - cy, mouse.x - cx)
                                if (angle < 0) angle += 2 * Math.PI
                                root.currentHue = angle / (2 * Math.PI)
                            }

                            onPressed: (mouse) => {
                                handleTouch(mouse)
                                bridge.save_setting("theme.main", root.selectedColor.toString())
                            }
                            onPositionChanged: (mouse) => {
                                handleTouch(mouse)
                                bridge.save_setting("theme.main", root.selectedColor.toString())
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Raccourcis de couleurs prédéfinies
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter
                        spacing: 10

                        Repeater {
                            model: root.quickPresets
                            Rectangle {
                                width: 36; height: 36; radius: 18
                                color: modelData
                                border.width: String(T.StyleManager.rawAccent).toLowerCase() === String(modelData).toLowerCase() ? 3 : 1.5
                                border.color: String(T.StyleManager.rawAccent).toLowerCase() === String(modelData).toLowerCase() ? "#FFFFFF" : "#4B5563"

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        const c = Qt.color(modelData)
                                        root.currentHue = c.hsvHue >= 0 ? c.hsvHue : 0.0
                                        bridge.save_setting("theme.main", String(modelData))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
