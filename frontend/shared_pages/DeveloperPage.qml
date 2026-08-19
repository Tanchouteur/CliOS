import QtQuick
import QtQuick.Layouts
import "components"
import "../style" as T
import "../state" as S

Item {
    id: root
    signal backRequested()
    readonly property var signals: S.UiState.debugSignals

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        PageHeader { Layout.fillWidth: true; title: "Développeur · CAN"; subtitle: root.signals.length + " signaux structurés"; onBackClicked: root.backRequested() }
        Card {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Données brutes normalisées"
            GridView {
                anchors.fill: parent; clip: true
                cellWidth: width / 3; cellHeight: 72; model: root.signals
                delegate: Rectangle {
                    width: GridView.view.cellWidth - 10; height: 62
                    radius: T.StyleManager.radiusSmall; color: index % 2 ? T.StyleManager.surfaceRaised : T.StyleManager.surfaceSoft
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 2
                            Text { Layout.fillWidth: true; text: modelData.domain + " · " + modelData.key; color: T.StyleManager.textSecondary; font.pixelSize: 13; elide: Text.ElideRight }
                            Text { Layout.fillWidth: true; text: modelData.source + " · " + modelData.quality; color: modelData.quality === "STALE" ? T.StyleManager.warning : T.StyleManager.textSecondary; font.pixelSize: 10; elide: Text.ElideRight }
                        }
                        Text {
                            Layout.preferredWidth: 130
                            text: (typeof modelData.value === "number" ? Number(modelData.value).toFixed(2) : String(modelData.value)) + (modelData.unit ? " " + modelData.unit : "")
                            color: T.StyleManager.text; font.family: "Monospace"; font.pixelSize: 14; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
