import QtQuick
import QtQuick.Layouts
import "../components"
import "../../../style" as T
import "../../../state" as S

Item {
    id: root
    signal backRequested()
    property var keys: Object.keys(S.UiState.vehicle).sort()

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 12
        GtPageHeader { Layout.fillWidth: true; title: "Développeur · CAN"; subtitle: root.keys.length + " valeurs exposées par le bridge"; onBackClicked: root.backRequested() }
        GtCard {
            Layout.fillWidth: true; Layout.fillHeight: true; title: "Données brutes normalisées"
            GridView {
                anchors.fill: parent; clip: true
                cellWidth: width / 3; cellHeight: 62; model: root.keys
                delegate: Rectangle {
                    width: GridView.view.cellWidth - 10; height: 52
                    radius: T.StyleManager.radiusSmall; color: index % 2 ? T.StyleManager.surfaceRaised : T.StyleManager.surfaceSoft
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 10; spacing: 12
                        Text { Layout.fillWidth: true; text: String(modelData); color: T.StyleManager.textSecondary; font.pixelSize: 14; elide: Text.ElideRight }
                        Text {
                            Layout.preferredWidth: 120
                            text: typeof S.UiState.vehicle[modelData] === "number" ? Number(S.UiState.vehicle[modelData]).toFixed(2) : String(S.UiState.vehicle[modelData])
                            color: T.StyleManager.text; font.family: "Monospace"; font.pixelSize: 15; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }
}
