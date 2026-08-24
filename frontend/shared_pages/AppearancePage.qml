import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T

Item {
    id: root
    property string initialRoute: "appearance"
    property int tab: initialRoute === "leds" ? 2 : (initialRoute === "accent" ? 1 : 0)
    property real currentHue: Math.max(0, T.StyleManager.rawAccent.hsvHue)
    readonly property color selectedColor: Qt.hsva(currentHue, 0.82, 0.96, 1)
    readonly property var tabs: ["STYLES", "COULEUR D’ACCENT", "ÉCLAIRAGES BLE"]
    readonly property var presets: ["#48B8FF", "#4DDB8A", "#FFB33B", "#FF4D5A", "#AF7CFF", "#F4F7FA"]
    signal styleRequested(string styleId)
    signal backRequested()
    onInitialRouteChanged: tab = initialRoute === "leds" ? 2 : (initialRoute === "accent" ? 1 : 0)

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Apparence"; subtitle: "Identité visuelle du cockpit et éclairages"; showBack: false }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 60; spacing: 10
            Repeater { model: root.tabs
                Button { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData; primary: root.tab === index; onClicked: root.tab = index }
            }
        }
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            GridView {
                anchors.fill: parent; visible: root.tab === 0; clip: true; interactive: false
                cellWidth: width / 3; cellHeight: height / 2
                model: T.StyleManager.styles
                delegate: Item {
                    width: GridView.view.cellWidth; height: GridView.view.cellHeight
                    Card {
                        anchors.fill: parent; anchors.margins: 6
                        title: modelData.label; highlighted: T.StyleManager.styleId === modelData.id
                        ColumnLayout { anchors.fill: parent; spacing: 7
                            Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: T.StyleManager.radiusSmall; color: modelData.palette.background; border.width: 1; border.color: modelData.palette.outline
                                Row { anchors.centerIn: parent; spacing: 12
                                    Rectangle { width: 54; height: 10; radius: 5; color: modelData.palette.surfaceRaised }
                                    Rectangle { width: 54; height: 10; radius: 5; color: modelData.palette.gaugeTrack }
                                    Rectangle { width: 54; height: 10; radius: 5; color: T.StyleManager.accent }
                                }
                            }
                            Text { Layout.fillWidth: true; text: modelData.description; color: T.StyleManager.textSecondary; font.pixelSize: 12; elide: Text.ElideRight }
                            Button { Layout.fillWidth: true; Layout.preferredHeight: 58; text: T.StyleManager.styleId === modelData.id ? "STYLE ACTIF" : "APPLIQUER"; primary: T.StyleManager.styleId === modelData.id; enabled: T.StyleManager.styleId !== modelData.id; onClicked: root.styleRequested(modelData.id) }
                        }
                    }
                }
            }
            RowLayout {
                anchors.fill: parent; visible: root.tab === 1; spacing: 18
                Card { Layout.fillWidth: true; Layout.fillHeight: true; title: "Couleur du cockpit"
                    ColumnLayout { anchors.fill: parent; spacing: 14
                        Text { Layout.fillWidth: true; text: "Touchez l’anneau pour modifier l’accent. La page reste ouverte pour comparer le résultat."; color: T.StyleManager.textSecondary; font.pixelSize: 16; wrapMode: Text.WordWrap }
                        Item { id: wheel; Layout.alignment: Qt.AlignHCenter; width: 300; height: 300
                            Canvas { anchors.fill: parent; onPaint: { const c = getContext("2d"); c.clearRect(0,0,width,height); for (let i=0;i<360;i+=2) { c.beginPath(); c.lineWidth=34; c.arc(width/2,height/2,112,(i-1)*Math.PI/180,(i+2)*Math.PI/180); c.strokeStyle=Qt.hsva(i/360,0.95,1,1); c.stroke() } } }
                            Rectangle { anchors.centerIn: parent; width: 150; height: 150; radius: 75; color: root.selectedColor; border.width: 4; border.color: T.StyleManager.surfaceRaised
                                Text { anchors.centerIn: parent; text: String(root.selectedColor).toUpperCase().substring(0,7); color: "white"; font.pixelSize: 18; font.bold: true }
                            }
                            MouseArea { anchors.fill: parent
                                function choose(mouse) { let a=Math.atan2(mouse.y-height/2,mouse.x-width/2); if(a<0)a+=2*Math.PI; root.currentHue=a/(2*Math.PI); bridge.save_setting("theme.main",root.selectedColor.toString()) }
                                onPressed: mouse => choose(mouse); onPositionChanged: mouse => { if (pressed) choose(mouse) }
                            }
                        }
                    }
                }
                Card { Layout.preferredWidth: 420; Layout.fillHeight: true; title: "Raccourcis"
                    GridLayout { anchors.fill: parent; columns: 2; rowSpacing: 16; columnSpacing: 16
                        Repeater { model: root.presets
                            Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 70; radius: T.StyleManager.radiusMedium; color: modelData; border.width: 3; border.color: String(T.StyleManager.rawAccent).toLowerCase() === modelData.toLowerCase() ? "white" : T.StyleManager.outline
                                MouseArea { anchors.fill: parent; onClicked: bridge.save_setting("theme.main", modelData) }
                            }
                        }
                    }
                }
            }
            Loader { anchors.fill: parent; visible: root.tab === 2; active: root.tab === 2; source: "LedManagerPage.qml" }
        }
    }
}
