import QtQuick
import QtQuick.Layouts
import "../components"
import "../style" as T

Item {
    id: root
    signal backRequested()
    readonly property var accents: ["#48B8FF", "#38D996", "#FFC247", "#FF5A67", "#FF4FA3", "#F4F7FA"]

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 14
        GtPageHeader { Layout.fillWidth: true; title: "Apparence"; subtitle: "Aperçu immédiat, enregistré dans le profil"; onBackClicked: root.backRequested() }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            Repeater {
                model: T.StyleManager.styles
                GtCard {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    title: modelData.label; highlighted: T.StyleManager.styleId === modelData.id
                    ColumnLayout {
                        anchors.fill: parent; spacing: 18
                        Text { Layout.fillWidth: true; text: modelData.description; color: T.StyleManager.textSecondary; font.pixelSize: 16; wrapMode: Text.WordWrap }
                        Item { Layout.fillHeight: true }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 120
                            radius: T.StyleManager.radiusMedium; color: modelData.palette.background
                            border.width: 1; border.color: T.StyleManager.accent
                            Row {
                                anchors.centerIn: parent; spacing: 16
                                Rectangle { width: 70; height: 12; radius: 6; color: modelData.palette.surfaceRaised }
                                Rectangle { width: 70; height: 12; radius: 6; color: modelData.palette.gaugeTrack }
                                Rectangle { width: 70; height: 12; radius: 6; color: T.StyleManager.accent }
                            }
                        }
                        GtButton { Layout.fillWidth: true; text: T.StyleManager.styleId === modelData.id ? "STYLE ACTIF" : "APPLIQUER"; primary: T.StyleManager.styleId === modelData.id; onClicked: T.StyleManager.selectStyle(modelData.id) }
                    }
                }
            }
            GtCard {
                Layout.preferredWidth: 300; Layout.minimumWidth: 300; Layout.maximumWidth: 300; Layout.fillHeight: true; title: "Accent"
                ColumnLayout {
                    anchors.fill: parent; spacing: 14
                    Text { Layout.fillWidth: true; text: "La couleur reste limitée aux sélections, progressions et détails lumineux."; color: T.StyleManager.textSecondary; font.pixelSize: 17; wrapMode: Text.WordWrap }
                    GridLayout {
                        Layout.alignment: Qt.AlignHCenter; columns: 3; columnSpacing: 18; rowSpacing: 18
                        Repeater {
                            model: root.accents
                            Rectangle {
                                width: 72; height: 72; radius: 36; color: modelData
                                border.width: String(T.StyleManager.rawAccent).toLowerCase() === String(modelData).toLowerCase() ? 5 : 2
                                border.color: T.StyleManager.text
                                MouseArea { anchors.fill: parent; onClicked: bridge.save_setting("theme.main", String(modelData)) }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
